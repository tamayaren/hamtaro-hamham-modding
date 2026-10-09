#include "gba.h"
#include "dialogue.h"

/* Dialogue tree: Clubhouse -> Boss -> Hamha -> response.
 * The event's ShowText command is at 0x0804ffb4; its unaligned text pointer
 * is at 0x0804ffb6 (original node: 0x0846cc6b).
 * mod.toml redirects that pointer to the named node below.
 *
 * Edit the strings, keeping lines short enough for the dialogue box.
 * \n starts a line; DIALOGUE_WAIT_LINE() waits for A before advancing/scrolling;
 * DIALOGUE_END() waits for A and finishes this node. Choices and conditional
 * routes belong to the game's event script, not to these text arrays.
 */
enum {
    /* Scene callback, not a universal portrait id. Sets Boss's idle animation,
     * which also loads his normal dialogue portrait. See kb/portraits.md. */
    Boss_IdleCallback = 0x08,
};

const u8 Mod_BossSunflowerDialogue[] = {
    DIALOGUE_CALL(Boss_IdleCallback),
    DIALOGUE_TEXT("There is a new sunflower\n"
                  "by the water."),
    DIALOGUE_END(),
};
