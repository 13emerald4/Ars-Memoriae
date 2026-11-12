import { useState, useRef, useEffect, useCallback } from 'react'
import {
  DEFAULT_TARGET_HIGHLIGHT_COLOR,
  PRESET_HIGHLIGHT_COLORS,
  hexToRgb,
  rgbToHex,
} from '../utils/expectedCodeUtils'

export interface HighlightColorPickerProps {
  color: string
  onChange: (hexColor: string) => void
  className?: string
}

export function HighlightColorPicker({
  color,
  onChange,
  className = '',
}: HighlightColorPickerProps) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const rgb = hexToRgb(color)
  const [red, setRed] = useState(rgb.r)
  const [green, setGreen] = useState(rgb.g)
  const [blue, setBlue] = useState(rgb.b)
  const [hexInput, setHexInput] = useState(color)

  // Keep local state in sync when color prop changes
  useEffect(() => {
    const parsed = hexToRgb(color)
    setRed(parsed.r)
    setGreen(parsed.g)
    setBlue(parsed.b)
    setHexInput(color)
  }, [color])

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen])

  const handleRgbChange = useCallback(
    (newR: number, newG: number, newB: number) => {
      const clampedR = Math.max(0, Math.min(255, newR))
      const clampedG = Math.max(0, Math.min(255, newG))
      const clampedB = Math.max(0, Math.min(255, newB))
      setRed(clampedR)
      setGreen(clampedG)
      setBlue(clampedB)
      const hex = rgbToHex(clampedR, clampedG, clampedB)
      setHexInput(hex)
      onChange(hex)
    },
    [onChange]
  )

  const handleHexSubmit = () => {
    const parsed = hexToRgb(hexInput)
    const validHex = rgbToHex(parsed.r, parsed.g, parsed.b)
    setRed(parsed.r)
    setGreen(parsed.g)
    setBlue(parsed.b)
    setHexInput(validHex)
    onChange(validHex)
  }

  return (
    <div ref={containerRef} className={`relative inline-block ${className}`}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center gap-1.5 px-2 py-0.5 rounded transition bg-[#161616] border border-ink-line hover:border-slate-500 text-xs text-slate-300 hover:text-white cursor-pointer shadow-xs"
        title="Choose highlight RGB color for expected solution code"
      >
        <span
          className="inline-block w-3 h-3 rounded-full border border-white/40 shadow-xs"
          style={{ backgroundColor: color }}
        />
        <span className="text-[11px] font-mono text-slate-400 hover:text-slate-200">Color</span>
      </button>

      {/* Popover Dropdown */}
      {isOpen && (
        <div className="absolute right-0 top-full mt-1.5 z-50 w-64 rounded-xl bg-[#1e1e1e] border border-ink-line/90 p-3 shadow-2xl text-xs space-y-3 animate-in fade-in zoom-in-95">
          <div className="flex items-center justify-between border-b border-ink-line/50 pb-2">
            <span className="font-semibold text-slate-200 text-xs flex items-center gap-1.5">
              <span>🎨</span> Highlight Color (RGB)
            </span>
            <button
              type="button"
              onClick={() => {
                const def = DEFAULT_TARGET_HIGHLIGHT_COLOR
                const p = hexToRgb(def)
                setRed(p.r)
                setGreen(p.g)
                setBlue(p.b)
                setHexInput(def)
                onChange(def)
              }}
              className="text-[10px] text-slate-400 hover:text-sky-300 underline cursor-pointer"
              title="Reset to default Emerald"
            >
              Reset
            </button>
          </div>

          {/* Quick Presets */}
          <div>
            <div className="text-[10px] font-medium text-slate-400 uppercase tracking-wider mb-1.5">
              Presets
            </div>
            <div className="flex items-center gap-1.5 justify-between">
              {PRESET_HIGHLIGHT_COLORS.map((preset) => {
                const isSelected = color.toLowerCase() === preset.hex.toLowerCase()
                return (
                  <button
                    key={preset.hex}
                    type="button"
                    onClick={() => {
                      const p = hexToRgb(preset.hex)
                      setRed(p.r)
                      setGreen(p.g)
                      setBlue(p.b)
                      setHexInput(preset.hex)
                      onChange(preset.hex)
                    }}
                    className={`w-6 h-6 rounded-full transition transform hover:scale-110 cursor-pointer flex items-center justify-center border ${
                      isSelected
                        ? 'ring-2 ring-white ring-offset-1 ring-offset-[#1e1e1e] border-white'
                        : 'border-white/20 hover:border-white/60'
                    }`}
                    style={{ backgroundColor: preset.hex }}
                    title={`${preset.name} (${preset.hex})`}
                  >
                    {isSelected && <span className="text-[10px] text-white drop-shadow">✓</span>}
                  </button>
                )
              })}
            </div>
          </div>

          {/* RGB Sliders & Native Picker */}
          <div className="space-y-2 pt-1 border-t border-ink-line/50">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-400 font-medium">RGB Sliders</span>
              <label className="flex items-center gap-1 text-[11px] text-sky-400 hover:text-sky-300 cursor-pointer">
                <span>Color Picker</span>
                <input
                  type="color"
                  value={color}
                  onChange={(e) => {
                    const hex = e.target.value
                    const p = hexToRgb(hex)
                    setRed(p.r)
                    setGreen(p.g)
                    setBlue(p.b)
                    setHexInput(hex)
                    onChange(hex)
                  }}
                  className="opacity-0 w-0 h-0 absolute pointer-events-none"
                />
              </label>
            </div>

            {/* Red */}
            <div className="flex items-center gap-2">
              <span className="w-3 text-[10px] font-bold text-rose-400 font-mono">R</span>
              <input
                type="range"
                min="0"
                max="255"
                value={red}
                onChange={(e) => handleRgbChange(Number(e.target.value), green, blue)}
                className="flex-1 accent-rose-500 h-1.5 bg-slate-700 rounded-lg cursor-pointer"
              />
              <span className="w-7 text-right font-mono text-[11px] text-slate-300">{red}</span>
            </div>

            {/* Green */}
            <div className="flex items-center gap-2">
              <span className="w-3 text-[10px] font-bold text-emerald-400 font-mono">G</span>
              <input
                type="range"
                min="0"
                max="255"
                value={green}
                onChange={(e) => handleRgbChange(red, Number(e.target.value), blue)}
                className="flex-1 accent-emerald-500 h-1.5 bg-slate-700 rounded-lg cursor-pointer"
              />
              <span className="w-7 text-right font-mono text-[11px] text-slate-300">{green}</span>
            </div>

            {/* Blue */}
            <div className="flex items-center gap-2">
              <span className="w-3 text-[10px] font-bold text-sky-400 font-mono">B</span>
              <input
                type="range"
                min="0"
                max="255"
                value={blue}
                onChange={(e) => handleRgbChange(red, green, Number(e.target.value))}
                className="flex-1 accent-sky-500 h-1.5 bg-slate-700 rounded-lg cursor-pointer"
              />
              <span className="w-7 text-right font-mono text-[11px] text-slate-300">{blue}</span>
            </div>
          </div>

          {/* Hex Input & Live Preview */}
          <div className="pt-2 border-t border-ink-line/50 flex items-center gap-2">
            <span className="text-[10px] font-mono text-slate-400">Hex:</span>
            <input
              type="text"
              value={hexInput}
              onChange={(e) => setHexInput(e.target.value)}
              onBlur={handleHexSubmit}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleHexSubmit()
                }
              }}
              className="w-20 px-1.5 py-0.5 rounded bg-[#121212] border border-ink-line text-[11px] font-mono text-slate-200 focus:outline-none focus:border-sky-500"
              placeholder="#10b981"
            />
            {/* Live swatch preview */}
            <div
              className="flex-1 px-2 py-0.5 rounded font-mono text-[10px] text-center border truncate font-medium"
              style={{
                backgroundColor: `rgba(${red}, ${green}, ${blue}, 0.18)`,
                borderColor: `rgb(${red}, ${green}, ${blue})`,
                color: `rgb(${Math.min(255, red + 60)}, ${Math.min(255, green + 60)}, ${Math.min(255, blue + 60)})`,
              }}
            >
              Preview
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
