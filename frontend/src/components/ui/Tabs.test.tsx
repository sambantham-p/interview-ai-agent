import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { Tabs, TabsContent, TabsList, TabsTrigger } from './Tabs'

describe('Tabs', () => {
  it('switches content when a trigger is chosen', async () => {
    const user = userEvent.setup()
    render(
      <Tabs defaultValue="a">
        <TabsList label="Sections">
          <TabsTrigger value="a" icon={<span />}>
            First
          </TabsTrigger>
          <TabsTrigger value="b" icon={<span />}>
            Second
          </TabsTrigger>
        </TabsList>
        <TabsContent value="a">Alpha body</TabsContent>
        <TabsContent value="b">Beta body</TabsContent>
      </Tabs>,
    )

    expect(screen.getByRole('tablist', { name: 'Sections' })).toBeInTheDocument()
    expect(screen.getByText('Alpha body')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Second' }))

    expect(screen.getByText('Beta body')).toBeInTheDocument()
    expect(screen.queryByText('Alpha body')).not.toBeInTheDocument()
  })
})
