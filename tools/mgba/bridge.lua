-- hamtools mGBA bridge
--
-- Loaded into mGBA 0.11+ with `mGBA.exe --script bridge.lua game.gba` (hamtools does this).
-- Listens on 127.0.0.1 (first free port in 61337..61346) and serves a line protocol:
--
--   request:  <id> <command> [args...]\n
--   response: {"id":<id>,"ok":true,"result":...}\n   or   {"id":<id>,"ok":false,"error":"..."}\n
--
-- Commands that span frames (wait, press) answer once the frames have run.
-- Watchpoints and breakpoints never pause the game: they record hits for later collection.

local BRIDGE_VERSION = 1
local PORT_FIRST, PORT_LAST = 61337, 61346

-- Log to mGBA's scripting console and to <repo>/.cache/mgba-bridge.log so agents can read it.
local LOG_PATH = nil
do
  local src = debug and debug.getinfo and debug.getinfo(1, 'S').source or ''
  local dir = src:match('^@(.*)[/\\]tools[/\\]mgba[/\\][^/\\]+$')
  if dir then LOG_PATH = dir .. '/.cache/mgba-bridge.log' end
end

local function log(level, msg)
  if level == 'error' then console:error(msg) else console:log(msg) end
  if LOG_PATH and io and io.open then
    local f = io.open(LOG_PATH, 'a')
    if f then f:write(os.date('%H:%M:%S '), level, ' ', msg, '\n'); f:close() end
  end
end

local server = nil
local clients = {}
local nextClient = 1
local pending = {}        -- frame-driven requests
local probes = {}         -- watch/break id -> probe record
local scriptKeys = 0      -- keys currently held by the bridge
local inRequest = false   -- true while a request handler runs (blocks re-entrant callbacks)

---------------------------------------------------------------------------
-- JSON encoding (responses only; requests are plain text)
---------------------------------------------------------------------------
local function jsonString(s)
  return '"' .. s:gsub('[%c"\\]', function(c)
    if c == '"' then return '\\"' end
    if c == '\\' then return '\\\\' end
    if c == '\n' then return '\\n' end
    return string.format('\\u%04x', c:byte())
  end) .. '"'
end

local function isArray(t)
  local n = 0
  for k in pairs(t) do
    if type(k) ~= 'number' then return false end
    n = n + 1
  end
  return n == #t
end

local function json(v)
  local t = type(v)
  if t == 'nil' then return 'null' end
  if t == 'boolean' then return tostring(v) end
  if t == 'number' then
    if v ~= v or v == math.huge or v == -math.huge then return 'null' end
    if math.type(v) == 'integer' then return string.format('%d', v) end
    return string.format('%.17g', v)
  end
  if t == 'string' then return jsonString(v) end
  if t == 'table' then
    local parts = {}
    if next(v) == nil then return '[]' end
    if isArray(v) then
      for _, item in ipairs(v) do parts[#parts + 1] = json(item) end
      return '[' .. table.concat(parts, ',') .. ']'
    end
    for k, item in pairs(v) do parts[#parts + 1] = jsonString(tostring(k)) .. ':' .. json(item) end
    return '{' .. table.concat(parts, ',') .. '}'
  end
  return jsonString(tostring(v))
end

---------------------------------------------------------------------------
-- helpers
---------------------------------------------------------------------------
local function toHex(s)
  return (s:gsub('.', function(c) return string.format('%02x', c:byte()) end))
end

local function fromHex(h)
  return (h:gsub('%x%x', function(b) return string.char(tonumber(b, 16)) end))
end

local function num(s, what)
  local v = s and tonumber(s)
  if v == nil then error('expected number for ' .. what .. ', got ' .. tostring(s)) end
  return math.tointeger(v) or v
end

local REGS = { 'r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7', 'r8', 'r9', 'r10', 'r11', 'r12',
               'sp', 'lr', 'pc', 'cpsr' }

local function readRegs()
  local out = {}
  for _, name in ipairs(REGS) do
    local ok, v = pcall(function() return emu:readRegister(name) end)
    if ok then out[name] = tonumber(v) or v end
  end
  return out
end

local function sendAll(client, data)
  local sock = client.sock
  local i = 1
  local n = #data
  local spins = 0
  while i <= n do
    local sent, err = sock:send(data, i, math.min(n, i + 65535))
    if sent == nil or (type(sent) == 'number' and sent < 0) then
      if err == socket.ERRORS.AGAIN then
        spins = spins + 1
        if spins > 100000 then return false end
      else
        return false
      end
    elseif type(sent) == 'number' and sent > 0 then
      i = i + sent
    else
      -- some builds return 0/true for a full write of the requested slice
      i = math.min(n, i + 65535) + 1
    end
  end
  return true
end

local function reply(client, id, ok, payload)
  local msg
  if ok then
    msg = '{"id":' .. json(id) .. ',"ok":true,"result":' .. json(payload) .. '}\n'
  else
    msg = '{"id":' .. json(id) .. ',"ok":false,"error":' .. json(tostring(payload)) .. '}\n'
  end
  if clients[client.cid] then sendAll(client, msg) end
end

---------------------------------------------------------------------------
-- probes (watchpoints / breakpoints) — record, never pause
---------------------------------------------------------------------------
local MAX_SITES = 256

local function recordHit(probe, extra)
  local regs = readRegs()
  local pc = regs.pc or -1
  local key = tostring(pc)
  local site = probe.sites[key]
  if not site then
    if probe.siteCount >= MAX_SITES then probe.dropped = probe.dropped + 1; return end
    site = { pc = pc, count = 0, first_frame = emu:currentFrame(), regs = regs, extra = extra }
    probe.sites[key] = site
    probe.siteCount = probe.siteCount + 1
  end
  site.count = site.count + 1
  site.last_frame = emu:currentFrame()
  probe.total = probe.total + 1
end

local WATCH_TYPES = { write = 1, read = 2, rw = 3, change = 5 }

local function addProbe(kind, addr, len, wtype)
  local probe = { kind = kind, address = addr, length = len, type = wtype,
                  sites = {}, siteCount = 0, total = 0, dropped = 0 }
  local cb = function(...)
    -- mGBA passes an info table (access details); flatten it to plain values
    local extra = nil
    for _, a in ipairs({ ... }) do
      if type(a) == 'table' or type(a) == 'userdata' then
        local ok = pcall(function()
          for k, v in pairs(a) do
            extra = extra or {}
            if type(v) ~= 'table' and type(v) ~= 'userdata' and type(v) ~= 'function' then extra[k] = v end
          end
        end)
        if not ok then extra = extra or { raw = tostring(a) } end
      end
    end
    recordHit(probe, extra)
  end
  local cbid
  if kind == 'break' then
    cbid = emu:setBreakpoint(cb, addr)
  elseif len > 1 then
    cbid = emu:setRangeWatchpoint(cb, addr, addr + len, WATCH_TYPES[wtype])
  else
    cbid = emu:setWatchpoint(cb, addr, WATCH_TYPES[wtype])
  end
  if cbid == nil or cbid < 0 then error('mGBA refused the ' .. kind .. 'point') end
  probe.cbid = cbid
  probes[cbid] = probe
  return cbid
end

local function probeReport(id, probe, clear)
  local sites = {}
  for _, s in pairs(probe.sites) do sites[#sites + 1] = s end
  table.sort(sites, function(a, b) return a.count > b.count end)
  local out = { id = id, kind = probe.kind, address = probe.address, length = probe.length,
                type = probe.type, total = probe.total, dropped = probe.dropped, sites = sites }
  if clear then
    probe.sites, probe.siteCount, probe.total, probe.dropped = {}, 0, 0, 0
  end
  return out
end

---------------------------------------------------------------------------
-- commands
---------------------------------------------------------------------------
local commands = {}

function commands.ping()
  return { bridge = BRIDGE_VERSION, title = emu:getGameTitle(), code = emu:getGameCode(),
           frame = emu:currentFrame(), port = server and server.port }
end

function commands.frame() return emu:currentFrame() end

function commands.read(args)
  local addr, len = num(args[1], 'address'), num(args[2] or '4', 'length')
  if addr >= 0x04000000 and addr < 0x05000000 then
    -- readRange can stall on I/O registers in mGBA 0.11-dev; read them 16 bits at a time
    local parts = {}
    local a = addr & ~1
    while a < addr + len do
      local v
      if a == 0x04000130 then
        -- reading KEYINPUT from a script hangs the request; synthesize it (active low)
        v = (~emu:getKeys()) & 0x3FF
      else
        v = emu:read16(a)
      end
      parts[#parts + 1] = string.char(v & 0xFF, (v >> 8) & 0xFF)
      a = a + 2
    end
    local s = table.concat(parts)
    local skip = addr - (addr & ~1)
    return toHex(s:sub(1 + skip, skip + len))
  end
  return toHex(emu:readRange(addr, len))
end

function commands.write(args)
  local addr, bytes = num(args[1], 'address'), fromHex(args[2] or '')
  for i = 1, #bytes do emu:write8(addr + i - 1, bytes:byte(i)) end
  return #bytes
end

function commands.write16(args) emu:write16(num(args[1], 'address'), num(args[2], 'value')); return true end
function commands.write32(args) emu:write32(num(args[1], 'address'), num(args[2], 'value')); return true end

function commands.regs() return readRegs() end

function commands.screenshot(_, rest)
  emu:screenshot(rest)
  return rest
end

function commands.save_state(_, rest)
  if not emu:saveStateFile(rest) then error('saveStateFile failed: ' .. rest) end
  return rest
end

function commands.load_state(_, rest)
  if not emu:loadStateFile(rest) then error('loadStateFile failed: ' .. rest) end
  return emu:currentFrame()
end

function commands.reset() emu:reset(); return true end

function commands.hold(args)
  scriptKeys = scriptKeys | num(args[1], 'keys')
  emu:addKeys(scriptKeys)
  return scriptKeys
end

function commands.release(args)
  local mask = args[1] and num(args[1], 'keys') or 0x3FF
  scriptKeys = scriptKeys & ~mask
  emu:clearKeys(mask)
  return scriptKeys
end

function commands.keys() return { held_by_bridge = scriptKeys, all = emu:getKeys() } end

-- frame-driven: return a pending record instead of a result
function commands.wait(args)
  return nil, { remaining = math.max(1, num(args[1] or '1', 'frames')) }
end

function commands.press(args)
  local mask = num(args[1], 'keys')
  local hold = math.max(1, num(args[2] or '6', 'hold frames'))
  local after = math.max(0, num(args[3] or '0', 'after frames'))
  scriptKeys = scriptKeys | mask
  emu:addKeys(mask)
  return nil, { remaining = hold, after = after, releaseMask = mask }
end

function commands.watch(args)
  local addr = num(args[1], 'address')
  local len = num(args[2] or '1', 'length')
  local wtype = args[3] or 'write'
  if not WATCH_TYPES[wtype] then error('watch type must be write|read|rw|change') end
  return addProbe('watch', addr, len, wtype)
end

commands['break'] = function(args)
  return addProbe('break', num(args[1], 'address'), 1, nil)
end

function commands.hits(args)
  local clear = args[2] ~= 'keep'
  if args[1] and args[1] ~= 'all' then
    local id = num(args[1], 'probe id')
    local probe = probes[id]
    if not probe then error('no probe ' .. id) end
    return { probeReport(id, probe, clear) }
  end
  local out = {}
  for id, probe in pairs(probes) do out[#out + 1] = probeReport(id, probe, clear) end
  return out
end

function commands.unprobe(args)
  local removed = {}
  for id, _ in pairs(probes) do
    if args[1] == nil or args[1] == 'all' or id == num(args[1], 'probe id') then
      emu:clearBreakpoint(id)
      removed[#removed + 1] = id
    end
  end
  for _, id in ipairs(removed) do probes[id] = nil end
  return removed
end

---------------------------------------------------------------------------
-- dispatch
---------------------------------------------------------------------------
local function handleLine(client, line)
  line = line:gsub('\r$', '')
  if line == '' then return end
  local id, cmd, rest = line:match('^(%S+)%s+(%S+)%s*(.*)$')
  if not id then reply(client, line, false, 'malformed request'); return end
  id = math.tointeger(tonumber(id)) or id
  local fn = commands[cmd]
  if not fn then reply(client, id, false, 'unknown command ' .. cmd); return end
  local args = {}
  for a in rest:gmatch('%S+') do args[#args + 1] = a end
  inRequest = true
  local ok, result, wait = pcall(fn, args, rest)
  inRequest = false
  if not ok then reply(client, id, false, result); return end
  if wait then
    wait.client, wait.id = client, id
    pending[#pending + 1] = wait
  else
    reply(client, id, true, result)
  end
end

local function onFrame()
  if #pending == 0 then return end
  local still = {}
  for _, p in ipairs(pending) do
    p.remaining = p.remaining - 1
    if p.remaining <= 0 then
      if p.releaseMask then
        scriptKeys = scriptKeys & ~p.releaseMask
        emu:clearKeys(p.releaseMask)
        p.releaseMask = nil
        if (p.after or 0) > 0 then
          p.remaining = p.after
          still[#still + 1] = p
        else
          reply(p.client, p.id, true, emu:currentFrame())
        end
      else
        reply(p.client, p.id, true, emu:currentFrame())
      end
    else
      still[#still + 1] = p
    end
  end
  pending = still
end

-- Re-apply bridge-held keys each time the game polls input, so the frontend's own
-- keyboard state can't silently drop them.
local function onKeysRead()
  if inRequest then return end
  if scriptKeys ~= 0 then emu:addKeys(scriptKeys) end
end

---------------------------------------------------------------------------
-- sockets
---------------------------------------------------------------------------
local function dropClient(client)
  if not clients[client.cid] then return end
  clients[client.cid] = nil
  local keep = {}
  for _, p in ipairs(pending) do if p.client ~= client then keep[#keep + 1] = p end end
  pending = keep
  pcall(function() client.sock:close() end)
end

local function onReceive(client)
  while clients[client.cid] do
    local data, err = client.sock:receive(65536)
    if data and #data > 0 then
      client.buf = client.buf .. data
      while true do
        local nl = client.buf:find('\n', 1, true)
        if not nl then break end
        local line = client.buf:sub(1, nl - 1)
        client.buf = client.buf:sub(nl + 1)
        handleLine(client, line)
      end
    else
      if err ~= socket.ERRORS.AGAIN then dropClient(client) end
      return
    end
  end
end

local function onAccept()
  local sock, err = server.sock:accept()
  if err or not sock then return end
  local client = { cid = nextClient, sock = sock, buf = '' }
  nextClient = nextClient + 1
  clients[client.cid] = client
  sock:add('received', function() onReceive(client) end)
  sock:add('error', function() dropClient(client) end)
end

local function start()
  for port = PORT_FIRST, PORT_LAST do
    local sock, err = socket.bind('127.0.0.1', port)
    if sock and not err then
      local _, lerr = sock:listen()
      if not lerr then
        server = { sock = sock, port = port }
        sock:add('received', onAccept)
        log('info', 'hamtools bridge listening on 127.0.0.1:' .. port)
        return
      end
      sock:close()
    end
  end
  log('error', 'hamtools bridge: no free port in ' .. PORT_FIRST .. '-' .. PORT_LAST)
end

local ok, err = xpcall(function()
  callbacks:add('frame', onFrame)
  callbacks:add('keysRead', onKeysRead)
  start()
end, debug and debug.traceback or tostring)
if not ok then log('error', 'hamtools bridge failed to start: ' .. tostring(err)) end
