use std::cmp::min;

#[derive(Debug, Clone, Copy)]
pub struct BitIndex {
    byte: usize,
    bit: u8,
}

impl BitIndex {
    pub fn new() -> BitIndex {
        BitIndex { byte: 0, bit: 0 }
    }

    pub fn advance(&mut self, num_bits: u8) {
        self.bit += num_bits;

        if self.bit >= 8 {
            self.byte += usize::from(self.bit / 8);
            self.bit %= 8;
        }
    }
}

/// (bits, num_bits_read)
pub fn next_bits(bytes: &[u8], i: &mut BitIndex, mut len: u8) -> (u16, u8) {
    assert!(len <= 16);

    let mut out = 0;
    let mut bits_emitted = 0;

    while len > 0 && i.byte < bytes.len() {
        let bits_remaining = 8 - i.bit;
        let bits_to_emit = min(bits_remaining, len);

        let bits = u16::from(bytes[i.byte] >> i.bit);
        out |= bits << bits_emitted;
        bits_emitted += bits_to_emit;

        assert!(bits_to_emit + i.bit <= 8);
        i.advance(bits_to_emit);

        len -= bits_to_emit;
    }

    (out, bits_emitted)
}
