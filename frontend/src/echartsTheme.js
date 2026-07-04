// Single source of truth for chart styling — warm Andean palette on light paper.
// Both the xy charts (chartLogic) and the choropleth maps (MapChart) read from
// here so the whole app is one design system.

export const PALETTE = [
  '#c85a34', // terracotta
  '#157a6e', // teal
  '#d99a2b', // ochre
  '#8a4a6b', // plum
  '#6f8f4e', // sage
  '#3f5aa6', // indigo
  '#e0895f', // coral
  '#a23b34', // brick
  '#4c7a86', // slate teal
  '#9c6b2f', // bronze
]

// warm sequential ramp for choropleths (low -> high)
export const SEQ = {
  light: ['#f6ecd9', '#f0d3a6', '#e6ac6b', '#d97f3f', '#c25728', '#8f3416'],
  dark: ['#f6ecd9', '#f0d3a6', '#e6ac6b', '#d97f3f', '#c25728', '#8f3416'],
}

export function tokens() {
  return {
    text: '#34291c', axis: '#8a7c68', grid: '#ece1cd',
    tooltipBg: '#fffdf7', tooltipBorder: '#e7dcc6',
    mapBorder: '#fffdf7', mapEmpty: '#efe5d2', mapLabel: '#34291c',
  }
}

export function tooltip(trigger = 'axis') {
  const t = tokens()
  return {
    trigger,
    backgroundColor: t.tooltipBg,
    borderColor: t.tooltipBorder,
    borderWidth: 1,
    padding: [9, 13],
    textStyle: { color: t.text, fontSize: 12.5, fontWeight: 500 },
    axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(200,90,52,.06)' } },
    extraCssText: 'box-shadow:0 8px 26px -8px rgba(80,50,20,.28);border-radius:11px;',
  }
}

export const FONT =
  '"Hanken Grotesk Variable", "Hanken Grotesk", system-ui, sans-serif'
