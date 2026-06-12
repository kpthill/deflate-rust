use std::collections::HashMap;

use anyhow::{bail, ensure, Result};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Symbol {
    Literal(u8),
    Length { num_bits: usize, base: u16 },
    EndOfBlock,
    Reserved,
}

#[derive(Debug)]
pub struct HuffmanTree {
    map: HashMap<CodePoint, Symbol>,
}

impl HuffmanTree {
    pub fn fixed_literal_len() -> HuffmanTree {
        let mut map = HashMap::<CodePoint, _>::new();

        for i in 0..=143 {
            let base = 0b_0011_0000_u16;
            let len = 8;

            map.insert(
                SpecCodePoint::new(base + u16::from(i), len).into(),
                Symbol::Literal(i),
            );
        }

        for i in 144..=255 {
            let offset = i - 144;
            let base = 0b_1_1001_0000_u16;
            let len = 9;

            map.insert(
                SpecCodePoint::new(base + u16::from(offset), len).into(),
                Symbol::Literal(i),
            );
        }

        // 256
        map.insert(SpecCodePoint::new(0, 7).into(), Symbol::EndOfBlock);

        for (i, num_bits, length_base) in HUFFMAN_LENGTH_MAPPING_7_BIT {
            let offset = i - 256;
            map.insert(
                SpecCodePoint::new(0 + offset, 7).into(),
                Symbol::Length {
                    num_bits,
                    base: length_base,
                },
            );
        }

        for (i, num_bits, length_base) in HUFFMAN_LENGTH_MAPPING_8_BIT {
            let offset = i - 280;
            map.insert(
                SpecCodePoint::new(0b_1100_0000_u16 + offset, 8).into(),
                Symbol::Length {
                    num_bits,
                    base: length_base,
                },
            );
        }

        map.insert(
            SpecCodePoint::new(0b_1100_0110_u16, 8).into(),
            Symbol::Reserved,
        );
        map.insert(
            SpecCodePoint::new(0b_1100_0111_u16, 8).into(),
            Symbol::Reserved,
        );

        HuffmanTree { map }
    }

    /// (sym, len)
    pub fn next_symbol(&self, (bits, max_len): (u16, usize)) -> Result<(Symbol, usize)> {
        for len in 1..=max_len {
            let code_point = CodePoint::new(bits, len);

            if let Some(symbol) = self.decode_symbol(code_point)? {
                return Ok((symbol, len));
            }
        }

        bail!("EOF reached before EOB -- 0x{bits:04x} {max_len}"); // 0xabcd
    }

    fn decode_symbol(&self, code_point: CodePoint) -> Result<Option<Symbol>> {
        let Some(&symbol) = self.map.get(&code_point) else {
            return Ok(None);
        };

        ensure!(symbol != Symbol::Reserved);
        Ok(Some(symbol))
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
struct CodePoint {
    bits: u16,
    len: usize,
}

impl CodePoint {
    fn new(bits: u16, len: usize) -> CodePoint {
        let mask = (1 << len) - 1;
        CodePoint {
            bits: bits & mask,
            len,
        }
    }
}

struct SpecCodePoint {
    len: usize,
    /// Bottom `len` many bits are filled, but in writing order (MSb0).
    bits: u16,
}

impl SpecCodePoint {
    fn new(bits: u16, len: usize) -> SpecCodePoint {
        SpecCodePoint { len, bits }
    }
}

impl From<SpecCodePoint> for CodePoint {
    fn from(m: SpecCodePoint) -> Self {
        Self {
            bits: m.bits.reverse_bits() >> (16 - m.len),
            len: m.len,
        }
    }
}

pub struct Distance {
    pub num_bits: usize,
    pub base: u16,
}

pub fn read_distance(window: u16, max_len: usize) -> Result<(Distance, usize)> {
    ensure!(max_len >= 5);
    let distance_code = window & 0b11111; // read 5 bits in fixed huffman
    let dist_spec_code_point = SpecCodePoint::new(distance_code, 5);
    let dist_code_point = CodePoint::from(dist_spec_code_point);
    Ok((distance_mapping(dist_code_point.bits)?, 5))
}

fn distance_mapping(bits: u16) -> Result<Distance> {
    let (num_bits, base) = match bits {
        0 => (0, 1),
        1 => (0, 2),
        2 => (0, 3),
        3 => (0, 4),
        4 => (1, 5),
        5 => (1, 7),
        6 => (2, 9),
        7 => (2, 13),
        8 => (3, 17),
        9 => (3, 25),
        10 => (4, 33),
        11 => (4, 49),
        12 => (5, 65),
        13 => (5, 97),
        14 => (6, 129),
        15 => (6, 193),
        16 => (7, 257),
        17 => (7, 385),
        18 => (8, 513),
        19 => (8, 769),
        20 => (9, 1025),
        21 => (9, 1537),
        22 => (10, 2049),
        23 => (10, 3073),
        24 => (11, 4097),
        25 => (11, 6145),
        26 => (12, 8193),
        27 => (12, 12289),
        28 => (13, 16385),
        29 => (13, 24577),
        _ => bail!("distance mapping {bits:05b} is not valid"),
    };
    Ok(Distance { num_bits, base })
}

/// (i, num_bits, base)
const HUFFMAN_LENGTH_MAPPING_7_BIT: [(u16, usize, u16); 23] = [
    (257, 0, 3),
    (258, 0, 4),
    (259, 0, 5),
    (260, 0, 6),
    (261, 0, 7),
    (262, 0, 8),
    (263, 0, 9),
    (264, 0, 10),
    (265, 1, 11),
    (266, 1, 13),
    (267, 1, 15),
    (268, 1, 17),
    (269, 2, 19),
    (270, 2, 23),
    (271, 2, 27),
    (272, 2, 31),
    (273, 3, 35),
    (274, 3, 43),
    (275, 3, 51),
    (276, 3, 59),
    (277, 4, 67),
    (278, 4, 83),
    (279, 4, 99),
];

/// (i, num_bits, base)
const HUFFMAN_LENGTH_MAPPING_8_BIT: [(u16, usize, u16); 6] = [
    (280, 4, 115),
    (281, 5, 131),
    (282, 5, 163),
    (283, 5, 195),
    (284, 5, 227),
    (285, 0, 258),
];
