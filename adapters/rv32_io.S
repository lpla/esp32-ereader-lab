/* Runtime board-input transport. No allocator, filesystem or renderer patches.
 * Addresses and schedule are supplied by the pin-checked host adapter. */
.option norvc
.include "settings.inc"
.section .text
.global adc_stub, gpio_stub, millis_stub
adc_stub:
  li t0, CONTROL
  lw t1, 0(t0)
  li t2, 1
  bne a1, t2, 1f
  addi t1, t1, 1
  sw t1, 0(t0)
  lw t2, 8(t0)
  bltu t1, t2, 1f
  ebreak
1:
  li a3, 4095
  bnez a1, 2f
  li a3, 3200
2:
  lw a4, 4(t0)
  li a5, TABLE
3:
  beqz a4, 5f
  lw a6, 0(a5)
  bne a1, a6, 4f
  lw a6, 4(a5)
  bleu t1, a6, 4f
  lw a6, 8(a5)
  bgtu t1, a6, 4f
  lw a3, 12(a5)
4:
  addi a5, a5, 16
  addi a4, a4, -1
  j 3b
5:
  sw a3, 0(a2)
  li a0, 0
  ret
gpio_stub:
  li t0, BOOT_CALLER
  beq ra, t0, 6f
  li t0, 6
  beq a0, t0, 6f
  li a0, 1
  ret
6:
  li a0, 0
  ret
millis_stub:
  addi sp, sp, -16
  sw ra, 12(sp)
  li t0, TIMER
  jalr ra, t0, 0
  li a2, 1000
  li a3, 0
  li t0, DIV64
  jalr ra, t0, 0
  li t0, CONTROL
  lw t1, 0(t0)
  li t2, 250
  bleu t1, t2, 7f
  sub t1, t1, t2
  li t2, 20
  mul t1, t1, t2
  add a0, a0, t1
7:
  lw ra, 12(sp)
  addi sp, sp, 16
  ret
