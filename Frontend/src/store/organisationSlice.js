/**
 * organisationSlice.js
 * =====================
 * Redux slice for multi-tenant organisation context.
 * Populated from JWT claims on login / org switch.
 */

import { createSlice } from '@reduxjs/toolkit'

const organisationSlice = createSlice({
  name: 'organisation',
  initialState: {
    // Active organisation the user is operating in
    activeOrg: null,        // { id, name, slug, subscription_plan }
    activeRole: null,       // 'ADMIN' | 'ANALYST' | 'AUDITOR' | 'VIEWER'
    // If user belongs to multiple orgs, this list is returned on login
    availableOrgs: [],      // [{ organisation_id, organisation_name, organisation_slug, role }]
    requiresOrgSelection: false,
  },
  reducers: {
    setActiveOrganisation: (state, action) => {
      const { organisation, role } = action.payload
      state.activeOrg            = organisation
      state.activeRole           = role
      state.requiresOrgSelection = false
      state.availableOrgs        = []
    },
    setAvailableOrganisations: (state, action) => {
      state.availableOrgs        = action.payload
      state.requiresOrgSelection = true
      state.activeOrg            = null
      state.activeRole           = null
    },
    clearOrganisation: (state) => {
      state.activeOrg            = null
      state.activeRole           = null
      state.availableOrgs        = []
      state.requiresOrgSelection = false
    },
  },
})

export const {
  setActiveOrganisation,
  setAvailableOrganisations,
  clearOrganisation,
} = organisationSlice.actions

export default organisationSlice.reducer
