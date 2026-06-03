import Ajv2020 from 'ajv/dist/2020'
import type { ErrorObject } from 'ajv'
import type { RuntimeWorkflow, ValidateIssue } from './types'
import schemaJson from '@contracts/workflow-runtime.schema.json'

let validateFn: ReturnType<Ajv2020['compile']> | null = null

function getValidate(): ReturnType<Ajv2020['compile']> {
  if (!validateFn) {
    const ajv = new Ajv2020({ allErrors: true, strict: false })
    validateFn = ajv.compile(schemaJson as object)
  }
  return validateFn!
}

export function validateRuntimeSchema(runtime: RuntimeWorkflow): ValidateIssue[] {
  const validate = getValidate()
  const ok = validate(runtime)
  if (ok) return []
  const errs = (validate.errors ?? []) as ErrorObject[]
  return errs.map((e) => ({
    path: e.instancePath || e.schemaPath || '',
    message: e.message ? `${e.keyword}: ${e.message}` : e.keyword,
  }))
}
