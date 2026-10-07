/* Shared definitions for Hamtaro mods. Game symbols from kb/symbols.csv are available to the
 * linker by name; declare the ones you use, e.g.  extern u16 gPlayerX;  */
#ifndef HAMTARO_GBA_H
#define HAMTARO_GBA_H

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed char s8;
typedef signed short s16;
typedef signed int s32;
typedef volatile u16 vu16;
typedef volatile u32 vu32;

#define REG_DISPCNT  (*(vu16 *)0x04000000)
#define REG_VCOUNT   (*(vu16 *)0x04000006)
#define REG_KEYINPUT (*(vu16 *)0x04000130)

#define KEY_A      0x0001
#define KEY_B      0x0002
#define KEY_SELECT 0x0004
#define KEY_START  0x0008
#define KEY_RIGHT  0x0010
#define KEY_LEFT   0x0020
#define KEY_UP     0x0040
#define KEY_DOWN   0x0080
#define KEY_R      0x0100
#define KEY_L      0x0200

#define RGB5(r, g, b) ((u16)((r) | ((g) << 5) | ((b) << 10)))

#endif
