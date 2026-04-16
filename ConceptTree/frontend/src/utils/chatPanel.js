const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

export function getChatPanelLimits(viewport = {}) {
  const viewportWidth = viewport.width ?? 1440;
  const viewportHeight = viewport.height ?? 900;

  return {
    minWidth: 280,
    maxWidth: Math.max(320, Math.min(560, viewportWidth - 40)),
    minHeight: 360,
    maxHeight: Math.max(420, Math.min(760, viewportHeight - 120)),
  };
}

export function clampChatPanelSize(size, viewport) {
  const limits = getChatPanelLimits(viewport);

  return {
    width: clamp(size.width, limits.minWidth, limits.maxWidth),
    height: clamp(size.height, limits.minHeight, limits.maxHeight),
  };
}

export function getDefaultChatPanelSize(viewport) {
  return clampChatPanelSize(
    {
      width: 320,
      height: 420,
    },
    viewport,
  );
}

export function getResizedChatPanelSize(startSize, deltaX, deltaY, viewport) {
  return clampChatPanelSize(
    {
      width: startSize.width + deltaX,
      height: startSize.height - deltaY,
    },
    viewport,
  );
}
