import * as RadixTabs from '@radix-ui/react-tabs'


export const Tabs = RadixTabs.Root

export function TabsList({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <RadixTabs.List
      aria-label={label}
      className="grid grid-flow-col auto-cols-[minmax(max-content,1fr)] gap-1 overflow-x-auto rounded-2xl bg-[#e8eef5] p-1.5"
    >
      {children}
    </RadixTabs.List>
  )
}

interface TabsTriggerProps {
  value: string
  icon: React.ReactNode
  children: React.ReactNode
}

export function TabsTrigger({ value, icon, children }: TabsTriggerProps) {
  return (
    <RadixTabs.Trigger
      value={value}
      className="group flex items-center justify-center gap-2 whitespace-nowrap rounded-xl px-4 py-3 text-[14px] font-semibold text-muted transition-all cursor-pointer hover:text-ink focus-visible:outline-2 focus-visible:outline-brand data-[state=active]:bg-white data-[state=active]:text-ink data-[state=active]:shadow-[0_2px_8px_-2px_rgba(10,23,48,0.2)]"
    >
      <span className="text-faint transition-colors group-data-[state=active]:text-brand">{icon}</span>
      {children}
    </RadixTabs.Trigger>
  )
}

export function TabsContent({ value, children }: { value: string; children: React.ReactNode }) {
  return (
    <RadixTabs.Content value={value} className="pt-7 focus-visible:outline-none">
      {children}
    </RadixTabs.Content>
  )
}
