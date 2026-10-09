/* Authored text for byte-array initializers, expanded by hamtools patch build.
 *
 * Each const u8 array is a named text node. Branching, choices and tree mapping
 * stay in event scripts; these helpers do not implement arbitrary branches.
 *
 * Example:
 *   const u8 Mod_Greeting[] = {
 *       DIALOGUE_TEXT("Hello!\n" "There is a new sunflower."),
 *       DIALOGUE_WAIT_LINE(), DIALOGUE_END()
 *   };
 *
 * Supported text: space, A-Z, a-z, 0-9, .!?-_,'()<>/ and backslash,
 * curly double quotes, closing single quote, and \n (line break).
 * Use C's \\ for a displayed backslash and curly quotes for quoted speech.
 * Other glyphs are rejected. End/wait/callback controls must be added explicitly.
 */
#ifndef HAMTARO_DIALOGUE_H
#define HAMTARO_DIALOGUE_H

/* Literal calls are replaced before GCC sees them. Fail if compiled unprepared. */
#define DIALOGUE_TEXT(text) HAMTOOLS_DIALOGUE_TEXT_REQUIRES_PATCH_BUILD

#define DIALOGUE_END()       0xe0
#define DIALOGUE_WAIT_LINE() 0xe3

/* Invoke a scene-specific callback. The id is not an established portrait id. */
#define DIALOGUE_CALL(id)    0xf4, (id)

#endif
