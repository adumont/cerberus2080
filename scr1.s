.pc02 ; 65C02 mode
.debuginfo      +       ; Generate debug info
.feature string_escapes

;	*= $8000
.segment  "CODE"

CURS = $FE
VRAM = $F800
MAILFLAG = $0200
MAILBOX  = $0201

RES_vec:
  CLD             ; clear decimal mode
  LDX #$FF
  TXS             ; set the stack pointer
  CLI

  ; Init CURSOR addr
  lda #<VRAM
  sta CURS
  lda #>VRAM
  sta CURS+1

  ; jsr clear_screen

  ldy #00
  stz $0200

@wait_key:
  lda MAILFLAG
  beq @wait_key

  lda MAILBOX

  cmp #8
  beq @backspace

  ; sta $f800,y
  sta (CURS),y
  iny           ; INC_CURSOR --> iny, if y=0 INC CURS+1... check if last line, then scroll up
  bra @clear

@backspace:
  lda #' '

  ; dey only if not 0
  cpy #0
  beq @skip
  dey           ; DEC_CURSOR
@skip:
  sta $f800,Y

@clear:
  stz $0200

  bra @wait_key

@end:
  BRA @end

;--------------------------------------

clear_screen:
  lda #' '

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

; Interrupts routines

IRQ_vec:
NMI_vec:
	RTI

;	*= $0200
.segment  "BSS"

LATEST:	.res 2	; Store the latest ADDR of the Dictionary

; Base of user memory area.
USER_BASE:

; system vectors

;    *=  $FFFA
.segment  "VECTORS"	

    .addr   NMI_vec     ; NMI vector
    .addr   RES_vec     ; RESET vector
    .addr   IRQ_vec     ; IRQ vector
