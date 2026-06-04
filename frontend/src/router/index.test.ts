import { describe, expect, it } from 'vitest'
import router from './index'

describe('workflow menu routes', () => {
  it.each([
    ['/workflow/index', 'workflow-list'],
    ['/workflow/global-config', 'workflow-global-config'],
    ['/workflow/queue', 'workflow-queue-list'],
  ])('resolves %s to %s', (path, name) => {
    const resolved = router.resolve(path)
    expect(resolved.name).toBe(name)
  })
})
