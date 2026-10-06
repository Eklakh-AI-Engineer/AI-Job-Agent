"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { kbApi, ApiError } from "@/lib/api";
import {
  APPROVED_TARGET_ROLES,
  WORK_MODES,
  candidateKBToForm,
  emptyProfileForm,
  formToCandidateKB,
  validateProfileForm,
  type ClaimForm,
  type ExperienceForm,
  type PreferencesForm,
  type ProfileForm,
  type ProjectForm,
} from "@/lib/kb";
import { TopBar } from "@/components/TopBar";
import { Button, ErrorText, Input, Select, Spinner, Textarea } from "@/components/ui";
import { ChipInput, FieldError, RepeatCard, Section } from "@/components/forms";

const SKILL_SUGGESTIONS = [
  "Python",
  "RAG",
  "LLM",
  "FastAPI",
  "SQL",
  "PyTorch",
  "TypeScript",
  "Docker",
  "Kubernetes",
  "AWS",
];

const LOCATION_SUGGESTIONS = ["Remote", "US", "UK", "UAE", "Canada", "Germany"];

export default function ProfileBuilderPage() {
  const [form, setForm] = useState<ProfileForm>(emptyProfileForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [version, setVersion] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [attempted, setAttempted] = useState(false);
  const idCounter = useRef(0);

  const uid = useCallback((prefix: string) => {
    idCounter.current += 1;
    return `${prefix}-${Date.now().toString(36)}-${idCounter.current}`;
  }, []);

  const applyForm = useCallback((next: ProfileForm) => setForm(next), []);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const res = await kbApi.get(true);
        if (!active) return;
        applyForm(candidateKBToForm(res.data));
        setVersion(res.version);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          applyForm(emptyProfileForm());
        } else if (active) {
          setError((err as Error).message);
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [applyForm]);

  const errors = attempted ? validateProfileForm(form) : {};

  // --- generic updates ---
  const update = (patch: Partial<ProfileForm>) =>
    setForm((f) => ({ ...f, ...patch }));
  const updatePrefs = (patch: Partial<PreferencesForm>) =>
    setForm((f) => ({ ...f, preferences: { ...f.preferences, ...patch } }));

  // --- skills (ChipInput surfaces names; disclosure preserved by name) ---
  function setSkillNames(names: string[]) {
    setForm((f) => ({
      ...f,
      skills: names.map((name) => {
        const existing = f.skills.find(
          (s) => s.name.toLowerCase() === name.toLowerCase(),
        );
        return (
          existing ?? {
            id: uid("SKILL"),
            name,
            verified: false,
            disclosure: "public",
          }
        );
      }),
    }));
  }

  // --- experience ---
  function addExperience() {
    setForm((f) => ({
      ...f,
      experience: [
        ...f.experience,
        {
          id: uid("EXP"),
          role: "",
          company: "",
          location: "",
          workMode: "",
          startDate: "",
          endDate: "",
          description: "",
        },
      ],
    }));
  }
  const updateExperience = (id: string, patch: Partial<ExperienceForm>) =>
    setForm((f) => ({
      ...f,
      experience: f.experience.map((e) => (e.id === id ? { ...e, ...patch } : e)),
    }));
  const removeExperience = (id: string) =>
    setForm((f) => ({ ...f, experience: f.experience.filter((e) => e.id !== id) }));

  // --- projects ---
  function addProject() {
    setForm((f) => ({
      ...f,
      projects: [
        ...f.projects,
        { id: uid("PROJ"), title: "", skills: [], description: "", url: "" },
      ],
    }));
  }
  const updateProject = (id: string, patch: Partial<ProjectForm>) =>
    setForm((f) => ({
      ...f,
      projects: f.projects.map((p) => (p.id === id ? { ...p, ...patch } : p)),
    }));
  const removeProject = (id: string) =>
    setForm((f) => ({ ...f, projects: f.projects.filter((p) => p.id !== id) }));

  // --- claims ---
  function addClaim() {
    setForm((f) => ({
      ...f,
      claims: [
        ...f.claims,
        { id: uid("CLAIM"), text: "", relatedSkills: [], disclosure: "public" },
      ],
    }));
  }
  const updateClaim = (id: string, patch: Partial<ClaimForm>) =>
    setForm((f) => ({
      ...f,
      claims: f.claims.map((c) => (c.id === id ? { ...c, ...patch } : c)),
    }));
  const removeClaim = (id: string) =>
    setForm((f) => ({ ...f, claims: f.claims.filter((c) => c.id !== id) }));

  // --- target roles ---
  const approvedSelected = form.targetRoles.filter((r) =>
    (APPROVED_TARGET_ROLES as readonly string[]).includes(r),
  );
  const customRoles = form.targetRoles.filter(
    (r) => !(APPROVED_TARGET_ROLES as readonly string[]).includes(r),
  );
  function toggleRole(role: string) {
    setForm((f) => ({
      ...f,
      targetRoles: f.targetRoles.includes(role)
        ? f.targetRoles.filter((r) => r !== role)
        : [...f.targetRoles, role],
    }));
  }
  function setCustomRoles(next: string[]) {
    setForm((f) => ({ ...f, targetRoles: [...approvedSelected, ...next] }));
  }

  // --- actions ---
  async function onValidate() {
    setAttempted(true);
    setError("");
    setMessage("");
    if (Object.keys(validateProfileForm(form)).length > 0) return;
    setValidating(true);
    try {
      const res = await kbApi.validate(formToCandidateKB(form));
      if (res.valid) setMessage("Profile is valid and ready to save.");
      else setError(res.errors.join("; "));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setValidating(false);
    }
  }

  async function onSave() {
    setAttempted(true);
    setError("");
    setMessage("");
    if (Object.keys(validateProfileForm(form)).length > 0) {
      setError("Please fix the highlighted fields before saving.");
      return;
    }
    setSaving(true);
    try {
      const kb = formToCandidateKB(form);
      const res = await kbApi.save(kb, "Updated via profile builder");
      setVersion(res.version);
      setMessage(`Saved as version ${res.version}.`);
      // Resync with the canonical, server-validated document.
      applyForm(candidateKBToForm(res.data));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div>
        <TopBar title="Candidate Profile" />
        <Spinner label="Loading your profile…" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <TopBar
        title="Candidate Profile"
        subtitle={
          version
            ? `Knowledge base · version ${version}`
            : "Build your career profile — no code required."
        }
        actions={
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              loading={validating}
              onClick={onValidate}
            >
              Validate
            </Button>
            <Button size="sm" loading={saving} onClick={onSave}>
              Save
            </Button>
          </div>
        }
      />

      {error ? <ErrorText>{error}</ErrorText> : null}
      {message ? (
        <div className="rounded-lg border border-success/20 bg-success/5 px-3 py-2 text-sm text-success">
          {message}
        </div>
      ) : null}

      {/* 1. Identity & Education */}
      <Section
        title="Identity & Education"
        description="Who you are and where you studied."
      >
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <Input
              label="Full name"
              value={form.fullName}
              onChange={(e) => update({ fullName: e.target.value })}
              placeholder="Ada Lovelace"
            />
            <FieldError>{errors.fullName}</FieldError>
          </div>
          <div>
            <Input
              label="Email"
              type="email"
              value={form.email}
              onChange={(e) => update({ email: e.target.value })}
              placeholder="you@example.com"
            />
            <FieldError>{errors.email}</FieldError>
          </div>
          <Input
            label="Degree"
            value={form.degree}
            onChange={(e) => update({ degree: e.target.value })}
            placeholder="B.S."
          />
          <Input
            label="Field of study"
            value={form.fieldOfStudy}
            onChange={(e) => update({ fieldOfStudy: e.target.value })}
            placeholder="Computer Science"
          />
          <Input
            label="Institution"
            value={form.institution}
            onChange={(e) => update({ institution: e.target.value })}
            placeholder="MIT"
          />
          <div>
            <Input
              label="Graduation year"
              inputMode="numeric"
              value={form.graduationYear}
              onChange={(e) => update({ graduationYear: e.target.value })}
              placeholder="2024"
            />
            <FieldError>{errors.graduationYear}</FieldError>
          </div>
        </div>
      </Section>

      {/* 2. Target Roles */}
      <Section
        title="Target Roles"
        description="Roles the agent should match you against."
      >
        <div className="flex flex-wrap gap-2">
          {APPROVED_TARGET_ROLES.map((role) => {
            const selected = form.targetRoles.includes(role);
            return (
              <button
                key={role}
                type="button"
                onClick={() => toggleRole(role)}
                className={`rounded-full border px-3 py-1.5 text-sm font-medium transition-colors ${
                  selected
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border text-muted hover:border-primary/40 hover:text-foreground"
                }`}
              >
                {selected ? "✓ " : ""}
                {role}
              </button>
            );
          })}
        </div>
        <FieldError>{errors.targetRoles}</FieldError>

        <div className="mt-4">
          <ChipInput
            label="Custom roles (optional)"
            value={customRoles}
            onChange={setCustomRoles}
            placeholder="e.g. Applied Scientist"
            idPrefix="role"
          />
          <p className="mt-1 text-xs text-muted">
            Custom roles are shown for planning; only the supported roles above
            are saved to your profile.
          </p>
        </div>
      </Section>

      {/* 3. Skills */}
      <Section
        title="Skills"
        description="Add the skills you want matched. Press Enter to add each one."
      >
        <ChipInput
          value={form.skills.map((s) => s.name)}
          onChange={setSkillNames}
          placeholder="Type a skill and press Enter (e.g. Python)"
          suggestions={SKILL_SUGGESTIONS}
          idPrefix="skill"
        />
      </Section>

      {/* 4. Work Experience */}
      <Section
        title="Work Experience"
        description="Add your roles, most recent first."
        action={
          <Button size="sm" variant="secondary" onClick={addExperience}>
            + Add experience
          </Button>
        }
      >
        {form.experience.length === 0 ? (
          <p className="text-sm text-muted">No experience added yet.</p>
        ) : (
          <div className="space-y-4">
            {form.experience.map((exp, i) => (
              <RepeatCard
                key={exp.id}
                title="Experience"
                index={i}
                onRemove={() => removeExperience(exp.id)}
              >
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <Input
                    label="Job title"
                    value={exp.role}
                    onChange={(e) => updateExperience(exp.id, { role: e.target.value })}
                    placeholder="ML Engineer"
                  />
                  <Input
                    label="Company"
                    value={exp.company}
                    onChange={(e) =>
                      updateExperience(exp.id, { company: e.target.value })
                    }
                    placeholder="Acme Corp"
                  />
                  <Input
                    label="Location"
                    value={exp.location}
                    onChange={(e) =>
                      updateExperience(exp.id, { location: e.target.value })
                    }
                    placeholder="Remote"
                  />
                  <Select
                    label="Work mode"
                    value={exp.workMode}
                    onChange={(e) =>
                      updateExperience(exp.id, { workMode: e.target.value })
                    }
                  >
                    <option value="">Not specified</option>
                    {WORK_MODES.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </Select>
                  <Input
                    label="Start date"
                    value={exp.startDate}
                    onChange={(e) =>
                      updateExperience(exp.id, { startDate: e.target.value })
                    }
                    placeholder="2023-06"
                  />
                  <Input
                    label="End date"
                    value={exp.endDate}
                    onChange={(e) =>
                      updateExperience(exp.id, { endDate: e.target.value })
                    }
                    placeholder="Present"
                  />
                </div>
                <div className="mt-3">
                  <Textarea
                    label="Description"
                    rows={3}
                    value={exp.description}
                    onChange={(e) =>
                      updateExperience(exp.id, { description: e.target.value })
                    }
                    placeholder="What did you build or achieve?"
                  />
                </div>
              </RepeatCard>
            ))}
          </div>
        )}
      </Section>

      {/* 5. Projects */}
      <Section
        title="Projects"
        description="Showcase work that demonstrates your skills."
        action={
          <Button size="sm" variant="secondary" onClick={addProject}>
            + Add project
          </Button>
        }
      >
        {form.projects.length === 0 ? (
          <p className="text-sm text-muted">No projects added yet.</p>
        ) : (
          <div className="space-y-4">
            {form.projects.map((proj, i) => (
              <RepeatCard
                key={proj.id}
                title="Project"
                index={i}
                onRemove={() => removeProject(proj.id)}
              >
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <Input
                    label="Project name"
                    value={proj.title}
                    onChange={(e) => updateProject(proj.id, { title: e.target.value })}
                    placeholder="RAG Document Assistant"
                  />
                  <Input
                    label="URL (optional)"
                    value={proj.url}
                    onChange={(e) => updateProject(proj.id, { url: e.target.value })}
                    placeholder="https://github.com/..."
                  />
                </div>
                <div className="mt-3">
                  <ChipInput
                    label="Technologies / skills"
                    value={proj.skills}
                    onChange={(skills) => updateProject(proj.id, { skills })}
                    placeholder="Type a technology and press Enter"
                    suggestions={SKILL_SUGGESTIONS}
                    idPrefix={`proj-${proj.id}`}
                  />
                </div>
                <div className="mt-3">
                  <Textarea
                    label="Description"
                    rows={3}
                    value={proj.description}
                    onChange={(e) =>
                      updateProject(proj.id, { description: e.target.value })
                    }
                    placeholder="Summarize the project and your impact."
                  />
                </div>
              </RepeatCard>
            ))}
          </div>
        )}
      </Section>

      {/* 6. Claims & Achievements */}
      <Section
        title="Claims & Achievements"
        description="Concrete, verifiable evidence used to strengthen your applications."
        action={
          <Button size="sm" variant="secondary" onClick={addClaim}>
            + Add claim
          </Button>
        }
      >
        {form.claims.length === 0 ? (
          <p className="text-sm text-muted">No claims added yet.</p>
        ) : (
          <div className="space-y-4">
            {form.claims.map((claim, i) => (
              <RepeatCard
                key={claim.id}
                title="Claim"
                index={i}
                onRemove={() => removeClaim(claim.id)}
              >
                <Textarea
                  label="Claim / achievement"
                  rows={2}
                  value={claim.text}
                  onChange={(e) => updateClaim(claim.id, { text: e.target.value })}
                  placeholder="e.g. Built a RAG pipeline serving 50k queries/month"
                />
                <div className="mt-3">
                  <ChipInput
                    label="Related skills"
                    value={claim.relatedSkills}
                    onChange={(relatedSkills) =>
                      updateClaim(claim.id, { relatedSkills })
                    }
                    placeholder="Link skills this claim supports"
                    suggestions={form.skills.map((s) => s.name)}
                    idPrefix={`claim-${claim.id}`}
                  />
                </div>
              </RepeatCard>
            ))}
          </div>
        )}
      </Section>

      {/* 7. Work Preferences */}
      <Section
        title="Work Preferences"
        description="What kind of role and setup you're looking for."
      >
        <div className="space-y-5">
          <div>
            <span className="mb-1 block text-xs font-medium text-muted">
              Work mode
            </span>
            <div className="flex flex-wrap gap-2">
              {WORK_MODES.map((mode) => {
                const selected = form.preferences.workModes.includes(mode);
                return (
                  <button
                    key={mode}
                    type="button"
                    onClick={() =>
                      updatePrefs({
                        workModes: selected
                          ? form.preferences.workModes.filter((m) => m !== mode)
                          : [...form.preferences.workModes, mode],
                      })
                    }
                    className={`rounded-full border px-3 py-1.5 text-sm font-medium capitalize transition-colors ${
                      selected
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border text-muted hover:border-primary/40 hover:text-foreground"
                    }`}
                  >
                    {mode}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <ChipInput
              label="Preferred locations"
              value={form.preferences.preferredLocations}
              onChange={(preferredLocations) => updatePrefs({ preferredLocations })}
              placeholder="e.g. Remote, US"
              suggestions={LOCATION_SUGGESTIONS}
              idPrefix="pref-loc"
            />
            <ChipInput
              label="Authorized to work in"
              value={form.preferences.authorizedLocations}
              onChange={(authorizedLocations) => updatePrefs({ authorizedLocations })}
              placeholder="e.g. US, UK"
              suggestions={LOCATION_SUGGESTIONS}
              idPrefix="auth-loc"
            />
          </div>

          <div className="flex flex-wrap gap-6">
            <label className="flex items-center gap-2 text-sm text-foreground">
              <input
                type="checkbox"
                checked={form.preferences.willingToRelocate}
                onChange={(e) =>
                  updatePrefs({ willingToRelocate: e.target.checked })
                }
                className="h-4 w-4 rounded border-border"
              />
              Willing to relocate
            </label>
            <label className="flex items-center gap-2 text-sm text-foreground">
              <input
                type="checkbox"
                checked={form.preferences.requiresVisaSponsorship}
                onChange={(e) =>
                  updatePrefs({ requiresVisaSponsorship: e.target.checked })
                }
                className="h-4 w-4 rounded border-border"
              />
              I require visa sponsorship
            </label>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <Input
                label="Minimum annual compensation"
                inputMode="numeric"
                value={form.preferences.compensationMin}
                onChange={(e) => updatePrefs({ compensationMin: e.target.value })}
                placeholder="e.g. 120000"
              />
              <FieldError>{errors.compensation}</FieldError>
            </div>
            <Select
              label="Currency"
              value={form.preferences.compensationCurrency}
              onChange={(e) =>
                updatePrefs({ compensationCurrency: e.target.value })
              }
            >
              {["USD", "EUR", "GBP", "AED", "INR", "CAD"].map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <ChipInput
              label="Excluded companies"
              value={form.preferences.excludedCompanies}
              onChange={(excludedCompanies) => updatePrefs({ excludedCompanies })}
              placeholder="Companies to avoid"
              idPrefix="excl-co"
            />
            <ChipInput
              label="Excluded domains"
              value={form.preferences.excludedDomains}
              onChange={(excludedDomains) => updatePrefs({ excludedDomains })}
              placeholder="Domains to avoid (e.g. gambling)"
              idPrefix="excl-dom"
            />
          </div>
        </div>
      </Section>

      <div className="flex items-center justify-end gap-3 pb-4">
        <Button variant="secondary" loading={validating} onClick={onValidate}>
          Validate
        </Button>
        <Button loading={saving} onClick={onSave}>
          Save profile
        </Button>
      </div>
    </div>
  );
}
