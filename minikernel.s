.pc02 ; 65C02 mode
; .debuginfo      +       ; Generate debug info
.feature string_escapes

LINE = $FE ; and $FF       ; ADDR (2 bytes), store a LINE ADDR
ROW = LINE - 1 
COL = ROW - 1

VRAM = $F800
MAILFLAG = $0200
MAILBOX  = $0201

MAX_ROW = 30
MAX_COL = 40
CURSOR  = '_'
SPACE   = ' '

.ifdef EMULATOR
; key codes on Emulator
KBD_RET  = $0A  ; Return
KBD_BACK = $08  ; Backspace
.else
; key codes on Cerberus
KBD_RET  = $0D  ; Return
KBD_BACK = $7F  ; Backspace
.endif

.segment  "CODE"
RES_vec:
  ; populate Interrupts vectors (in Cerberus RAM)
  lda #<NMI_vec
  sta $FFFA
  lda #>NMI_vec
  sta $FFFB
  lda #<IRQ_vec
  sta $FFFE
  lda #>IRQ_vec
  sta $FFFF

  CLD             ; clear decimal mode
  LDX #$FF
  TXS             ; set the stack pointer
  CLI

  ; start at line 0, col 0
  stz ROW
  stz COL

  ; store addr of line 0
  lda #<VRAM
  sta LINE
  lda #>VRAM
  sta LINE+1

  lda #CURSOR
  ldy COL
  sta (LINE),y 

  ; jsr clear_screen

  ldy #0
  sty COL
  stz MAILFLAG

loop:
  jsr put_cursor
  jsr getc
  jsr putc
  bra loop

getc:
@wait_key:
  ; wai       ; I can't make it work in py65... :(
  lda MAILFLAG
  beq @wait_key

  lda MAILBOX

  stz MAILFLAG

  rts

putc:
  cmp #KBD_BACK
  beq @backspace

  cmp #KBD_RET
  beq @return

  ldy COL
  sta (LINE),y
  inc COL
  
  cpy #MAX_COL-1
  beq @return
  rts

@return:
  jsr erase_cursor

; reached end of line or Return
  ; COL<-0
  stz COL
  ldy COL

; last row?
  lda ROW
  cmp #MAX_ROW-1
  bne @not_last_row
; yes last row --> don't inc ROW, scroll everything up

  jsr scroll_up
  rts

; else (not last row)
@not_last_row:  
  ; LINE<-LINE+MAX_COL
  clc
  lda LINE
  adc #MAX_COL
  sta LINE
  lda LINE+1
  adc #0
  sta LINE+1
  ; ROW++
  inc ROW   
  rts

@backspace:
  jsr erase_cursor
  ; dey only if not 0
  cpy #0
  bne @goleft1col
  ; we are at the beginning of a line:
  ; if first line: can't do anything
  lda ROW
  cmp #0
  beq @erase
  ; otherwise: move up 1 line:
  dea
  sta ROW
  ; LINE -= MAX_COL
  sec 
  lda LINE
  sbc #MAX_COL
  sta LINE
  lda LINE+1
  sbc #0
  sta LINE+1
  ; place cursor on the last col
  ldy #MAX_COL-1
  sty COL

  bra @erase
@goleft1col:
  dey
  sty COL
@erase:
  lda #SPACE
  sta (LINE),y

  rts



;--------------------------------------

erase_cursor:
  pha
  lda #SPACE
  ldy COL
  sta (LINE),y
  pla
  rts

put_cursor:
  lda #CURSOR
  ldy COL
  sta (LINE),y
  rts


;--------------------------------------

clear_screen:
  lda #SPACE

  ldy #$00
next:
  sta VRAM,y
  sta VRAM+$100,y
  sta VRAM+$200,y
  sta VRAM+$300,y

  dey
  bne next

  ldy #$af
next2:
  sta VRAM+$400,y

  dey
  bne next2
  sta VRAM+$400,y
  RTS


scroll_up:
  ; Scroll screen UP (and clears last line), long... ¿fast?
  phy
  ldy #00
@next:
  lda $F828,y
  sta $F800,y
  lda $F850,y 
  sta $F828,y
  lda $F878,y 
  sta $F850,y
  lda $F8A0,y 
  sta $F878,y
  lda $F8C8,y 
  sta $F8A0,y
  lda $F8F0,y 
  sta $F8C8,y
  lda $F918,y 
  sta $F8F0,y
  lda $F940,y 
  sta $F918,y
  lda $F968,y 
  sta $F940,y
  lda $F990,y 
  sta $F968,y
  lda $F9B8,y 
  sta $F990,y
  lda $F9E0,y 
  sta $F9B8,y
  lda $FA08,y 
  sta $F9E0,y
  lda $FA30,y 
  sta $FA08,y
  lda $FA58,y 
  sta $FA30,y
  lda $FA80,y 
  sta $FA58,y
  lda $FAA8,y 
  sta $FA80,y
  lda $FAD0,y 
  sta $FAA8,y
  lda $FAF8,y 
  sta $FAD0,y
  lda $FB20,y 
  sta $FAF8,y
  lda $FB48,y 
  sta $FB20,y
  lda $FB70,y 
  sta $FB48,y
  lda $FB98,y 
  sta $FB70,y
  lda $FBC0,y 
  sta $FB98,y
  lda $FBE8,y 
  sta $FBC0,y
  lda $FC10,y 
  sta $FBE8,y
  lda $FC38,y 
  sta $FC10,y
  lda $FC60,y 
  sta $FC38,y
  lda $FC88,y 
  sta $FC60,y
  lda #SPACE
  sta $FC88,y
  iny
  cpy #$28
  beq @end
  jmp @next
@end:
  ply
  rts

; Interrupts routines
IRQ_vec:
NMI_vec:
	RTI

