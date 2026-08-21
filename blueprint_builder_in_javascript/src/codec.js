export async function encodeBlueprint(blueprint) {
  const bytes = new TextEncoder().encode(JSON.stringify(blueprint));
  const stream = new Blob([bytes]).stream().pipeThrough(new CompressionStream("deflate"));
  const compressed = new Uint8Array(await new Response(stream).arrayBuffer());
  let binary = "";
  for (let offset = 0; offset < compressed.length; offset += 0x8000) {
    binary += String.fromCharCode(...compressed.subarray(offset, offset + 0x8000));
  }
  return `0${btoa(binary)}`;
}
