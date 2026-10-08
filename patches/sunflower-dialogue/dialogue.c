#include "gba.h"

enum {
    Text_Space = 0x01,
    Text_CapitalT = 0x1f,
    Text_Period = 0xca,
    Text_EndWait = 0xe0,
    Text_Newline = 0xe2,
    Text_SetPortrait = 0xf4,
};

/* Original text authored for this mod. The two lines fit Boss's dialogue box.
 * Encoding and controls: kb/dialogue.md. */
const u8 Mod_BossSunflowerDialogue[] = {
    Text_SetPortrait, 0x08,
    Text_CapitalT, 'h', 'e', 'r', 'e', Text_Space,
    'i', 's', Text_Space, 'a', Text_Space, 'n', 'e', 'w', Text_Space,
    's', 'u', 'n', 'f', 'l', 'o', 'w', 'e', 'r', Text_Newline,
    'b', 'y', Text_Space, 't', 'h', 'e', Text_Space,
    'w', 'a', 't', 'e', 'r', Text_Period, Text_EndWait,
};
