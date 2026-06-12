use std::fs;

use anyhow::Result;

fn main() -> Result<()> {
    let uncompressed_bytes = fs::read("examples/lookback_and_repeat.txt")?;
    let compressed_bytes = fs::read("examples/lookback_and_repeat.txt.deflate")?;
    let decompressed = deflate_rust::decompress(&compressed_bytes)?;
    assert_eq!(uncompressed_bytes, decompressed);
    println!("{}", str::from_utf8(&decompressed)?);
    Ok(())
}
