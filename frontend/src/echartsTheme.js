// Single source of truth for chart styling. Both the xy charts (chartLogic)
// and the choropleth maps (MapChart) pull tokens from here so the whole app
// reads as one design system in light and dark.

export const PALETTE = [
  '#2563eb', '#e0603a', '#2e9e83', '#e0a53a', '#8256c4',
  '#3aa0e0', '#d1477a', '#5aa02e', '#9c7b3a', '#54617a',
]

// sequential ramp for choropleths (low -> high), tuned per theme
export const SEQ = {
  light: ['#eef4fb', '#c7dcf2', '#8fb8e3', '#4f8bd0', '#1f5fae', '#123f77'],
  dark: ['#16233a', '#1e3a63', '#2b5a8f', '#3f7fc0', '#6fa8e0', '#a9ccf2'],
}

export function tokens(dark) {
  return dark
    ? {
        text: '#e6eaf2', axis: '#8a93a6', grid: '#232a38',
        tooltipBg: '#141a24', tooltipBorder: '#2b3446',
        mapBorder: '#0e1420', mapEmpty: '#1b2432', mapLabel: '#c3ccdb',
      }
    : {
        text: '#1a2230', axis: '#5a6472', grid: '#e7ebf1',
        tooltipBg: '#ffffff', tooltipBorder: '#dfe4ec',
        mapBorder: '#ffffff', mapEmpty: '#eef1f6', mapLabel: '#3a4453',
      }
}

// shared tooltip block
export function tooltip(dark, trigger = 'axis') {
  const t = tokens(dark)
  return {
    trigger,
    backgroundColor: t.tooltipBg,
    borderColor: t.tooltipBorder,
    borderWidth: 1,
    textStyle: { color: t.text, fontSize: 12.5 },
    axisPointer: { type: 'shadow' },
    extraCssText: 'box-shadow:0 4px 18px rgba(0,0,0,.18);border-radius:8px;',
  }
}

export const FONT =
  '"Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
