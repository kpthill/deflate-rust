use anyhow::{Result, bail, ensure};

use crate::{
    bitstream::BitIndex,
    huffman::{HuffmanTree, Symbol},
};

mod bitstream;
mod huffman;

pub fn decompress(bytes: &[u8]) -> Result<Vec<u8>> {
    ensure!(bytes.len() >= 2); // (?) -- other block types: are they ever THAT small?

    let mut out = vec![];

    let mut i = BitIndex::new();

    let header_bits = bytes[0] & 0x7;
    ensure!(header_bits == 0x3); // assuming single-block, fixed-tree
    i.advance(3);

    let tree = HuffmanTree::fixed_literal_len(); // (only, for now)

    // TODO: could maybe move window logic into its own file

    let (mut window, mut window_len) = bitstream::next_bits(bytes, &mut i, 16);

    loop {
        let (symbol, len) = tree.next_symbol(window, window_len)?;

        window >>= len;
        let (new_window_bits, bits_read) = bitstream::next_bits(bytes, &mut i, len);
        window |= new_window_bits << (16 - len);
        window_len -= len - bits_read;

        match symbol {
            Symbol::Literal(byte) => out.push(byte),
            Symbol::Length { .. } => todo!("!"),
            Symbol::EndOfBlock => return Ok(out),
            Symbol::Reserved => bail!("reserved symbol"),
        }
    }
}
