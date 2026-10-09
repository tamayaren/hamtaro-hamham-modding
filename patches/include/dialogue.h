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
 * Native letters (including accents), digits, punctuation and symbols are mapped
 * in kb/glyphs.md. Use UTF-8 source or C Unicode escapes. ASCII single/double
 * quotes select the closing quote; use curly opening quotes for quoted speech.
 * Use C's \\ for a displayed backslash. \n inserts a line break.
 * Named icons use DIALOGUE_GLYPH(HEART), etc.; see the constants below.
 * Characters absent from the font are errors; controls stay explicit in C.
 */
#ifndef HAMTARO_DIALOGUE_H
#define HAMTARO_DIALOGUE_H

/* Literal calls are replaced before GCC sees them. Fail if compiled unprepared. */
#define DIALOGUE_TEXT(text) HAMTOOLS_DIALOGUE_TEXT_REQUIRES_PATCH_BUILD

#define DIALOGUE_END()       0xe0
#define DIALOGUE_WAIT_LINE() 0xe3

/* Native shapes, including the three without an unambiguous Unicode character. */
#define DIALOGUE_GLYPH_BOXED_E        0x60
#define DIALOGUE_GLYPH_DEGREE         0xc1
#define DIALOGUE_GLYPH_RAISED_A_GRAVE 0xc2
#define DIALOGUE_GLYPH_HEART          0xdc
#define DIALOGUE_GLYPH_STAR           0xdd
#define DIALOGUE_GLYPH_MUSIC_NOTE     0xde
#define DIALOGUE_GLYPH_OUTLINE_CROSS  0xdf
#define DIALOGUE_GLYPH(name) DIALOGUE_GLYPH_##name

/* Invoke a scene-specific callback. The id is not an established portrait id. */
#define DIALOGUE_CALL(id)    0xf4, (id)

#endif
