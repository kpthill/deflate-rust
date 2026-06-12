use anyhow::{bail, ensure, Result};

use crate::{
    bitstream::Bitstream,
    huffman::{HuffmanTree, Symbol},
};

mod bitstream;
mod huffman;

pub fn decompress(bytes: &[u8]) -> Result<Vec<u8>> {
    ensure!(bytes.len() >= 2); // (?) -- other block types: are they ever THAT small?

    let mut out = vec![];

    let mut bs = Bitstream::new(bytes);

    let header_bits = bs.next_bits(3)?;
    ensure!(header_bits == 0x3); // assuming single-block, fixed-tree

    let tree = HuffmanTree::fixed_literal_len(); // (only, for now)

    loop {
        let (symbol, len) = tree.next_symbol(bs.peek())?;
        bs.advance(len as isize)?;

        dbg!(symbol);

        match symbol {
            Symbol::Literal(byte) => out.push(byte),
            Symbol::Length { num_bits, base } => {
                dbg!(bs.byte, bs.bit);

                let addend = bs.next_bits(num_bits)?;
                let length = base + addend;

                // TODO: This won't work for dynamic trees
                let (distance, _) = huffman::read_distance(bs.next_bits(5)?, 5)?;
                let dist_extra_bits = bs.next_bits(distance.num_bits)?;

                let dist: usize = (distance.base + dist_extra_bits).into();

                ensure!(out.len() >= dist);
                let mut read_idx = out.len() - dist;

                for _ in 0..length {
                    out.push(out[read_idx]);
                    read_idx += 1;
                }
            }
            Symbol::EndOfBlock => return Ok(out),
            Symbol::Reserved => bail!("reserved symbol"),
        }
    }
}
