@Echo off

REM Make a single binary of the code where all data exists!

python python\merge-binaries.py Rom\epr-10380b.133 Rom\epr-10382b.118 code1.bin 01
python python\merge-binaries.py Rom\epr-10381b.132 Rom\epr-10383b.117 code2.bin 02
copy /b code1.bin+code2.bin code.bin
del code1.bin
del code2.bin

REM test only as it outputs 256 files! python python\splitchunks.py outrun16.pal palettes.pal 48
REM save the games 5-5-5 palettes from the game rom binary
python python\savebit.py code.bin outrun_palettes.bin 14ed8 2000

REM we now convert them to 8bit RGB same method as how mame does it! No I didn't steal their code.
python python\palette5bit_to_8bit.py outrun_palettes.bin outrun16.pal

REM let's make a FO size image of the palettes as it just looks so cool!
python Python\palette_image2.py --columns 3 outrun16.pal outrun_palettes.png

REM Now move onto the sprites!
REM copy files from rom to here, just temp.
copy rom\mpr-103*.* .

REM merge all the images into one big daddy file, because it's a 68000 it's all high low order
python python\merge-binaries.py mpr-10373.10 mpr-10371.9 merge1.bin 01
python python\merge-binaries.py mpr-10377.12 mpr-10375.11 merge2.bin 01
python python\merge-binaries.py merge2.bin merge1.bin sprites1.bin 02
REM now merge the 2nd set of four files. See mames segaorun.cpp for the order
python python\merge-binaries.py mpr-10374.14 mpr-10372.13 merge1.bin 01
python python\merge-binaries.py mpr-10378.16 mpr-10376.15 merge2.bin 01
python python\merge-binaries.py merge2.bin merge1.bin sprites2.bin 02

REM just combine the two together so they are one
copy /b /y sprites1.bin+sprites2.bin all_sprites.bin
REM you can look now with something like BinXView can see the sprites select 4bit colour and change size!
REM and if you use the palettes from the above REM out splitchunks you can see the sprites as 4-bit RGB index

REM because of 68000k high/low order we swap over high low 4bits in the sprites
python Python\swapnybbles.py all_sprites.bin

REM this is a little test plot which let's you specify a sprite number and it uses the tables inside the ROM to get the details
python python\sprite_plot_index.py code.bin all_sprites.bin outrun16.pal 51 2 car1.png

REM this is main python script, I have to admit I had to cheat a little, outrun palette details are not inside any table
REM but scattered inside the sprite object creation and thus some are hard coded, so how do we get the values?
REM well I cheated, use mame debugger to trigger a display output for the offset in the palette handler, which I could then get the palette number
REM for the relivant sprite offset, there is a table of sprites, but this is not always used, which is kind of strange!
REM so we ended up with a offset and a palette dump from mame which I merged together and so we ended up with the setup_table.csv
python python\sprite_atlas.py code.bin all_sprites.bin outrun16.pal setup_table.csv sprite_variations.png --overlay sprite_variations_overlay.png --box sprites_variations_box.png --variations

REM this is the single non variations images
python python\sprite_atlas.py code.bin all_sprites.bin outrun16.pal setup_table.csv sprite_.png --overlay sprite_overlay.png --box sprites_box.png

REM the --variations option of you remove this it will only generate the sprites mosty which are the larger size
REM the table entries contain the sprite and scale values for additional sized down sprites. but the script can scan the addition 10 byte table for more entries until the next palette change, which would most of the time another sprite object

REM I did this because someone might want each sprite saved as a seperate file. and so it outputs every sprite into a folder as seperate file
REM additionally it makes a nice CSV with the sprite x,y and also the palette number, maybe someone has a need for this.
REM the -16 is a special option which saves the sprites as 16 bit index PNGs so this could be used for other platforms.
python python\sprites_extract.py code.bin all_sprites.bin outrun16.pal setup_table.csv sprites16col --variations -16
python python\sprites_extract.py code.bin all_sprites.bin outrun16.pal setup_table.csv sprites256bit --variations

REM one last note, the sprites in the ROM don't often use colours 0 and 15 colour 15 is a hardware used number to indicate an end of sprite data, this is why it's one big dirty chunk. Sega16 title all use same system, this is why in mame you can't see the sprites they are more genetic pure data sets, like most computers would use. and not character set based.

REM if you have questions email me @ mikeybabes@gmail.com and nice words please.
REM last thing is after I did all this I then come across reassembler on youtube, might of saved me some time! o well bollocks!


