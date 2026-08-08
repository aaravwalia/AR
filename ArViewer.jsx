import { useEffect, useState } from 'react';

/**
 * AR "View on your wall" preview for GPSFDK product pages.
 *
 * Usage:
 *   <ArViewer productId={product.slug} catalogUrl={import.meta.env.VITE_AR_CATALOG_URL} />
 *
 * - Matches the product by slug against catalog.json "id"
 * - Renders nothing if the product has no AR models yet (safe on every page)
 * - Requires the model-viewer script in client/index.html:
 *   <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js"></script>
 */
export default function ArViewer({ productId, catalogUrl }) {
  const [artwork, setArtwork] = useState(null);
  const [baseUrl, setBaseUrl] = useState('');
  const [notFound, setNotFound] = useState(false);
  const [pi, setPi] = useState(0);
  const [si, setSi] = useState(0);

  useEffect(() => {
    if (!catalogUrl || !productId) return;
    let alive = true;
    fetch(catalogUrl)
      .then((r) => r.json())
      .then((d) => {
        if (!alive) return;
        const found = d.artworks.find((a) => a.id === productId);
        if (!found) { setNotFound(true); return; }
        // models are served from the same folder as catalog.json
        setBaseUrl(catalogUrl.replace(/catalog\.json.*$/, ''));
        setArtwork(found);
      })
      .catch(() => setNotFound(true));
    return () => { alive = false; };
  }, [catalogUrl, productId]);

  // No AR for this product → render nothing (keeps the page clean)
  if (notFound || !artwork) return null;

  const product = artwork.products[pi];
  const size = product.sizes[si];
  const specLabel =
    size.unit === 'in' ? `${size.w}" × ${size.h}"` : `${size.w} × ${size.h}mm`;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 600 }}>
      <div style={{ position: 'relative', width: '100%', paddingBottom: '75%', background: '#f5f4f2', borderRadius: 10, overflow: 'hidden' }}>
        <model-viewer
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
          src={baseUrl + size.glb}
          ios-src={baseUrl + size.usdz}
          alt={`${artwork.name} — ${product.name} ${size.label}`}
          ar
          ar-modes="webxr scene-viewer quick-look"
          ar-placement="wall"
          ar-scale="fixed"
          camera-controls
          touch-action="pan-y"
          shadow-intensity="1"
          exposure="1.05"
          environment-image="neutral"
        >
          <button
            slot="ar-button"
            style={{
              position: 'absolute', bottom: 18, left: '50%', transform: 'translateX(-50%)',
              display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '13px 22px', background: '#C8A871', color: '#1a1813',
              border: 'none', borderRadius: 99, fontSize: 14, fontWeight: 600,
              cursor: 'pointer', boxShadow: '0 8px 24px rgba(0,0,0,.35)',
            }}
          >
            View on your wall
          </button>
        </model-viewer>
      </div>

      <div style={{ display: 'flex', gap: 16, alignItems: 'baseline' }}>
        <span style={{ fontSize: 20, fontWeight: 600 }}>{artwork.name}</span>
        <span style={{ fontFamily: 'monospace', fontSize: 13, color: '#8a6d3b' }}>
          {product.name} · {specLabel}
        </span>
      </div>

      {artwork.products.length > 1 && (
        <div>
          <div style={{ fontSize: 11, letterSpacing: '.15em', textTransform: 'uppercase', color: '#999', marginBottom: 8 }}>Format</div>
          <div style={{ display: 'flex', gap: 8 }}>
            {artwork.products.map((p, i) => (
              <button
                key={p.id}
                onClick={() => { setPi(i); setSi(0); }}
                style={{
                  padding: '8px 16px', borderRadius: 99, cursor: 'pointer', fontSize: 13,
                  border: i === pi ? '2px solid #C8A871' : '1px solid #ddd',
                  background: i === pi ? '#faf7f0' : 'transparent',
                  fontWeight: i === pi ? 600 : 400,
                }}
              >
                {p.name}
              </button>
            ))}
          </div>
        </div>
      )}

      <div>
        <div style={{ fontSize: 11, letterSpacing: '.15em', textTransform: 'uppercase', color: '#999', marginBottom: 8 }}>Size</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {product.sizes.map((s, i) => (
            <button
              key={i}
              onClick={() => setSi(i)}
              style={{
                padding: '10px 14px', textAlign: 'left', borderRadius: 8, cursor: 'pointer',
                border: i === si ? '2px solid #C8A871' : '1px solid #ddd',
                background: i === si ? '#faf7f0' : 'transparent',
              }}
            >
              <div style={{ fontSize: 14, fontWeight: i === si ? 600 : 400 }}>{s.label}</div>
              <div style={{ fontSize: 11, color: '#999', fontFamily: 'monospace' }}>
                {s.unit === 'in' ? `${s.w}" × ${s.h}"` : `${s.w} × ${s.h}mm`}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
