use anyhow::{bail, ensure, Result};
use std::cmp::min;

#[derive(Debug, Clone, Copy)]
pub struct Bitstream<'a> {
    // window: u16,
    // window_len: usize,
    pub byte: usize,
    pub bit: usize,
    bytes: &'a [u8],
}

impl<'a> Bitstream<'a> {
    pub fn new(bytes: &'a [u8]) -> Self {
        Self {
            byte: 0,
            bit: 0,
            bytes,
        }
    }

    pub fn len_remaining(&self) -> usize {
        if self.byte >= self.bytes.len() {
            return 0;
        }

        (self.bytes.len() - self.byte) * 8 - usize::from(self.bit)
    }

    pub fn peek(&mut self) -> (u16, usize) {
        let (window, wlen) = self.next_bits_dangerous(16);
        self.advance(-(wlen as isize)).unwrap();
        (window, wlen)
    }

    pub fn next_bits(&mut self, num_bits: usize) -> Result<u16> {
        let (res, bits_read) = self.next_bits_dangerous(num_bits);
        ensure!(num_bits == bits_read);
        Ok(res)
    }

    /// (bits, num_bits_read)
    fn next_bits_dangerous(&mut self, num_bits: usize) -> (u16, usize) {
        assert!(num_bits <= 16);

        let mut len = num_bits;
        let mut out = 0;
        let mut bits_emitted = 0;

        while len > 0 && self.byte < self.bytes.len() {
            let bits_remaining = 8 - self.bit;
            let bits_to_emit = min(bits_remaining, len);

            let bits = u16::from(self.bytes[self.byte] >> self.bit);
            out |= bits << bits_emitted;
            bits_emitted += bits_to_emit;

            assert!(bits_to_emit + self.bit <= 8);
            self.bit += bits_to_emit;

            if self.bit >= 8 {
                self.byte += usize::from(self.bit / 8);
                self.bit %= 8;
            }

            len -= bits_to_emit;
        }

        // mask away bits we shouldn't see
        let mask = 1_u16.unbounded_shl(num_bits as u32).wrapping_sub(1);
        out &= mask;

        (out, bits_emitted)
    }

    pub fn advance(&mut self, distance: isize) -> Result<()> {
        ensure!(distance <= self.len_remaining() as isize);
        ensure!(distance >= 0 || -distance <= (self.byte * 8 + self.bit as usize) as isize);

        let mut loc: isize = (self.byte * 8 + self.bit) as isize;
        loc += distance;
        self.byte = loc.div_euclid(8) as usize;
        self.bit = loc.rem_euclid(8) as usize;

        Ok(())
    }
}

#[test]
fn test_advance() {
    let bits = [0 as u8; 10];
    let mut bs = Bitstream::new(&bits);
    bs.advance(8);
    assert!(bs.bit == 0 && bs.byte == 1);
    bs.advance(13);
    assert!(bs.bit == 5 && bs.byte == 2);
    bs.advance(-15);
    assert!(bs.bit == 6 && bs.byte == 0);
    bs.advance(18);
    assert!(bs.bit == 0 && bs.byte == 3);
    bs.advance(-17);
    assert!(bs.bit == 7 && bs.byte == 0);
}
