import { useState, useRef, useEffect } from 'react'
import { X, Plus } from 'lucide-react'

interface Props {
  tags: string[]
  onTagsChange: (tags: string[]) => void
}

export function TagEditor({ tags, onTagsChange }: Props) {
  const [editing, setEditing] = useState(false)
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editing) inputRef.current?.focus()
  }, [editing])

  const removeTag = (idx: number) => {
    onTagsChange(tags.filter((_, i) => i !== idx))
  }

  const addTags = () => {
    const newTags = input
      .split(/[,，]/)
      .map(t => t.trim())
      .filter(t => t.length > 0 && !tags.includes(t))
    if (newTags.length > 0) {
      onTagsChange([...tags, ...newTags])
    }
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addTags()
    } else if (e.key === 'Escape') {
      setEditing(false)
      setInput('')
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-1 min-h-[20px]">
      {tags.map((tag, i) => (
        <span
          key={i}
          className="inline-flex items-center gap-0.5 bg-primary/10 text-primary text-[10px] px-1.5 py-0.5 rounded-full"
        >
          {tag}
          <button
            onClick={(e) => { e.stopPropagation(); removeTag(i) }}
            className="hover:text-red-500 transition-colors"
          >
            <X className="w-3 h-3" />
          </button>
        </span>
      ))}
      {editing ? (
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={() => { addTags(); setEditing(false) }}
          placeholder="标签, 逗号分隔"
          className="text-[10px] bg-transparent border-b border-primary/30 outline-none px-1 py-0.5 w-28"
        />
      ) : (
        <button
          onClick={() => setEditing(true)}
          className="inline-flex items-center gap-0.5 text-[10px] text-muted-foreground hover:text-primary transition-colors"
        >
          <Plus className="w-3 h-3" />
          {tags.length === 0 ? '标签' : ''}
        </button>
      )}
    </div>
  )
}
