// One adapter per ATS: the public endpoint and a pure normalizer to the unified schema.
// All five are the vendors' documented public job-board APIs (no auth, meant for embedding).

const decode = (s) =>
  String(s ?? "")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&");
export const htmlToText = (html) =>
  decode(decode(html).replace(/<(br|\/p|\/div|\/li|\/h\d)\s*\/?>/gi, "\n").replace(/<li[^>]*>/gi, "- ").replace(/<[^>]+>/g, ""))
    .replace(/[ \t]+/g, " ").replace(/\n\s*\n+/g, "\n\n").trim();
const iso = (v) => {
  if (v === undefined || v === null || v === "") return null;
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
};
const isRemote = (...parts) => /\bremote\b/i.test(parts.filter(Boolean).join(" "));

export const ATS = {
  greenhouse: {
    url: (slug) => `https://boards-api.greenhouse.io/v1/boards/${slug}/jobs?content=true`,
    list: (j) => j?.jobs ?? [],
    norm: (x, slug) => ({
      company: x.company_name ?? slug, ats: "greenhouse", jobId: String(x.id), title: x.title ?? "",
      location: x.location?.name ?? null, remote: isRemote(x.location?.name, x.title),
      department: x.departments?.[0]?.name ?? null, employmentType: null,
      postedAt: iso(x.first_published ?? x.updated_at), updatedAt: iso(x.updated_at),
      url: x.absolute_url ?? null, applyUrl: x.absolute_url ?? null, compensation: null,
      description: x.content ? htmlToText(x.content) : null,
    }),
  },
  lever: {
    url: (slug) => `https://api.lever.co/v0/postings/${slug}?mode=json`,
    list: (j) => (Array.isArray(j) ? j : []),
    norm: (x, slug) => ({
      company: slug, ats: "lever", jobId: String(x.id), title: x.text ?? "",
      location: x.categories?.location ?? null, remote: x.workplaceType === "remote" || isRemote(x.categories?.location),
      department: x.categories?.department ?? x.categories?.team ?? null, employmentType: x.categories?.commitment ?? null,
      postedAt: iso(x.createdAt), updatedAt: null,
      url: x.hostedUrl ?? null, applyUrl: x.applyUrl ?? null,
      compensation: x.salaryRange ? [x.salaryRange.min, x.salaryRange.max].filter((n) => n != null).join("-") + ` ${x.salaryRange.currency ?? ""} ${x.salaryRange.interval ?? ""}`.trimEnd() : null,
      description: x.descriptionPlain ?? (x.description ? htmlToText(x.description) : null),
    }),
  },
  ashby: {
    url: (slug) => `https://api.ashbyhq.com/posting-api/job-board/${slug}?includeCompensation=true`,
    list: (j) => j?.jobs ?? [],
    norm: (x, slug) => ({
      company: slug, ats: "ashby", jobId: String(x.id), title: x.title ?? "",
      location: x.location ?? null, remote: x.isRemote === true || isRemote(x.location),
      department: x.department ?? x.team ?? null, employmentType: x.employmentType ?? null,
      postedAt: iso(x.publishedAt), updatedAt: null,
      url: x.jobUrl ?? null, applyUrl: x.applyUrl ?? null,
      compensation: x.compensation?.compensationTierSummary ?? x.compensation?.scrapeableCompensationSalarySummary ?? null,
      description: x.descriptionPlain ?? (x.descriptionHtml ? htmlToText(x.descriptionHtml) : null),
    }),
  },
  workable: {
    url: (slug) => `https://apply.workable.com/api/v1/widget/accounts/${slug}?details=true`,
    list: (j) => j?.jobs ?? [],
    norm: (x, slug, j) => ({
      company: j?.name ?? slug, ats: "workable", jobId: String(x.shortcode ?? x.id ?? ""), title: x.title ?? "",
      location: [x.city, x.state, x.country].filter(Boolean).join(", ") || null, remote: x.telecommuting === true || isRemote(x.city, x.title),
      department: x.department ?? null, employmentType: x.employment_type ?? null,
      postedAt: iso(x.published_on ?? x.created_at), updatedAt: null,
      url: x.url ?? x.shortlink ?? null, applyUrl: x.application_url ?? x.url ?? null, compensation: null,
      description: x.description ? htmlToText(x.description) : null,
    }),
  },
  smartrecruiters: {
    url: (slug) => `https://api.smartrecruiters.com/v1/companies/${slug}/postings?limit=100`,
    list: (j) => j?.content ?? [],
    norm: (x, slug) => ({
      company: x.company?.name ?? slug, ats: "smartrecruiters", jobId: String(x.id), title: x.name ?? "",
      location: x.location?.fullLocation ?? [x.location?.city, x.location?.region, x.location?.country].filter(Boolean).join(", ") ?? null,
      remote: x.location?.remote === true || isRemote(x.name),
      department: x.department?.label ?? x.function?.label ?? null, employmentType: x.typeOfEmployment?.label ?? null,
      postedAt: iso(x.releasedDate), updatedAt: null,
      url: x.ref ? `https://jobs.smartrecruiters.com/${slug}/${x.id}` : null, applyUrl: `https://jobs.smartrecruiters.com/${slug}/${x.id}`, compensation: null,
      description: null, // the list endpoint has no description; kept null rather than one extra request per job
    }),
  },
};

const HOSTS = [
  [/(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io\/(?:embed\/job_board\?for=)?([\w-]+)/i, "greenhouse"],
  [/jobs(?:\.eu)?\.lever\.co\/([\w-]+)/i, "lever"],
  [/jobs\.ashbyhq\.com\/([\w.%-]+)/i, "ashby"],
  [/apply\.workable\.com\/([\w-]+)/i, "workable"],
  [/(?:jobs|careers)\.smartrecruiters\.com\/([\w-]+)/i, "smartrecruiters"],
];

/** "https://jobs.lever.co/spotify" | "greenhouse:stripe" | "stripe" -> [{ats, slug}] (bare slug = try all). */
export function parseCompany(raw) {
  const s = String(raw ?? "").trim();
  if (!s) return [];
  for (const [re, ats] of HOSTS) {
    const m = re.exec(s);
    if (m) return [{ ats, slug: decodeURIComponent(m[1]) }];
  }
  const pair = /^(\w+):([\w.-]+)$/.exec(s);
  if (pair && ATS[pair[1].toLowerCase()]) return [{ ats: pair[1].toLowerCase(), slug: pair[2] }];
  if (/^[\w.-]+$/.test(s)) return Object.keys(ATS).map((ats) => ({ ats, slug: s }));
  return [];
}

const any = (text, words) => !words?.length || words.some((w) => String(text ?? "").toLowerCase().includes(String(w).toLowerCase()));
export function keep(job, f) {
  if (!any(job.title, f.titleKeywords)) return false;
  if (!any(job.location, f.locationKeywords)) return false;
  if (f.remoteOnly && !job.remote) return false;
  if (f.postedAfter && (job.updatedAt ?? job.postedAt) && (job.updatedAt ?? job.postedAt) < f.postedAfter) return false;
  return true;
}
