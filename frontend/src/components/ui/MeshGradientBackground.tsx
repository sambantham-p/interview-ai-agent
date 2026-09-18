interface MeshGradientBackgroundProps {
  /** Dims the glow orbs ~35% - used by error/empty states (e.g.
   * NotFoundPage) so they read as a quieter variant of the hero rather
   * than a visual duplicate of the landing page. */
  muted?: boolean
}

// Mesh-gradient hero background: brand teal/navy glow orbs over a dark
// base, plus a faint dot grid for texture - no external image asset, so
// it never has a broken-image flash. Shared by every dark-hero page
// (Navigation's `transparent` prop) so the glow intensity can't drift
// between pages the way two independently-edited copies would.
export function MeshGradientBackground({ muted = false }: MeshGradientBackgroundProps) {
  const alphaScale = muted ? 0.6 : 1

  return (
    <div
      className="absolute inset-0 -z-10 bg-hero"
      style={{
        backgroundImage: [
          `radial-gradient(60% 50% at 15% 10%, rgba(24,169,153,${0.35 * alphaScale}), transparent 60%)`,
          `radial-gradient(50% 45% at 85% 20%, rgba(35,86,161,${0.45 * alphaScale}), transparent 60%)`,
          `radial-gradient(70% 60% at 50% 100%, rgba(18,42,80,${0.65 * alphaScale}), transparent 60%)`,
          `radial-gradient(circle, rgba(255,255,255,${0.08 * alphaScale}) 1px, transparent 1px)`,
        ].join(', '),
        backgroundSize: 'auto, auto, auto, 28px 28px',
      }}
      aria-hidden="true"
    />
  )
}
