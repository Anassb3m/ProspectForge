with open("app/templates/partials/sourcing_row.html", "w") as f:
    f.write("""<tr id="sourcing-row-{{ prospect.id }}" class="hover:bg-[#f9f9f8] transition group {% if prospect.acquisition_score >= 75 %}bg-[#ffebe6]/40{% elif prospect.acquisition_score >= 60 %}bg-[#fff3e0]/40{% endif %}">
  <td class="px-4 py-4 align-top">
    <a href="/prospects/{{ prospect.id }}" class="font-medium text-notion-text hover:text-notion-blue transition whitespace-normal max-w-[200px] block leading-snug">{{ prospect.company_name }}</a>
    <p class="text-[12px] text-notion-gray mt-1 whitespace-normal">
      {{ prospect.sector }} &middot; {{ prospect.company_size }}
      {% if prospect.naf_code %}<span class="font-mono text-[11px] bg-gray-100 px-1 rounded ml-1">{{ prospect.naf_code }}</span>{% endif %}
    </p>
    <p class="text-[11px] text-notion-gray mt-0.5 whitespace-normal">
      {% if prospect.city %}{{ prospect.city }}{% endif %}
      {% if prospect.department %} ({{ prospect.department }}){% endif %}
      {% if prospect.siret %}<span class="font-mono text-gray-400"> &middot; {{ prospect.siret }}</span>
      {% elif prospect.siren %}<span class="font-mono text-gray-400"> &middot; {{ prospect.siren }}</span>{% endif %}
    </p>
  </td>
  <td class="px-4 py-4 align-top">
    {% if prospect.decision_maker_name %}
    <span class="font-medium text-notion-text text-[13px] block leading-snug whitespace-normal">{{ prospect.decision_maker_name }}</span>
    <p class="text-[12px] text-notion-gray mt-0.5 whitespace-normal max-w-[150px]">{{ prospect.decision_maker_title or '—' }}</p>
    {% else %}
    <span class="text-[12px] text-notion-gray italic">No dirigeant yet</span>
    {% endif %}
  </td>
  <td class="px-4 py-4 align-top">
    <span class="inline-flex items-center rounded-sm px-2 py-0.5 text-[11px] font-medium border whitespace-nowrap {% if prospect.signal_type in ['DECP_WIN', 'PUBLIC_AWARD', 'BOAMP_WIN'] %}bg-blue-50 text-blue-700 border-blue-200{% elif prospect.signal_type == 'REGISTRY_FIELD' %}bg-gray-100 text-gray-600 border-gray-200{% else %}bg-orange-50 text-orange-700 border-orange-200{% endif %}">
      {{ prospect.signal_type }}
    </span>
    {% if prospect.award_count %}
    <p class="mt-1.5 text-[11px] text-notion-gray whitespace-nowrap">{{ prospect.award_count }} award(s)
      {% if prospect.award_total_value %}<br><span class="font-medium text-notion-text">≈{{ '{:,.0f}'.format(prospect.award_total_value).replace(',', ' ') }}€</span>{% endif %}
    </p>
    {% endif %}
  </td>
  <td class="px-4 py-4 align-top max-w-[280px]">
    <div class="flex flex-wrap gap-1.5 mb-2">
      {% for b in prospect.score_badges[:5] %}
      <span class="inline-flex items-center rounded-sm bg-gray-50 px-1.5 py-0.5 text-[10px] font-medium text-gray-600 border border-gray-200 shadow-sm">{{ b }}</span>
      {% endfor %}
    </div>
    {% if prospect.why_this_lead %}
    <ul class="text-[11px] text-notion-gray list-disc pl-3.5 space-y-1 whitespace-normal">
      {% for r in prospect.why_this_lead[:2] %}
      <li class="leading-relaxed">{{ r }}</li>
      {% endfor %}
    </ul>
    {% endif %}
  </td>
  <td class="px-4 py-4 align-top w-28">
    <div class="space-y-1 text-[11px] tabular-nums">
      <div class="flex justify-between items-center"><span class="text-notion-gray">ACQ</span><span class="font-semibold text-[12px] {% if prospect.acquisition_score >= 70 %}text-red-600{% elif prospect.acquisition_score >= 55 %}text-orange-600{% else %}text-notion-text{% endif %}">{{ prospect.acquisition_score }}</span></div>
      <div class="flex justify-between items-center"><span class="text-notion-gray">Fit</span><span class="text-gray-700">{{ prospect.fit_score }}</span></div>
      <div class="flex justify-between items-center"><span class="text-notion-gray">Time</span><span class="text-gray-700">{{ prospect.timing_score }}</span></div>
      <div class="flex justify-between items-center"><span class="text-notion-gray">Reach</span><span class="text-gray-700">{{ prospect.contactability_score }}</span></div>
    </div>
  </td>
  <td class="px-4 py-4 align-top">
    {% if prospect.contact_status == 'Verified email' %}
    <span class="inline-flex items-center rounded-sm bg-green-50 px-2 py-0.5 text-[11px] font-medium text-green-700 border border-green-200">
      <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
      {{ prospect.contact_status }}
    </span>
    {% elif 'Needs' in prospect.contact_status %}
    <span class="inline-flex items-center rounded-sm bg-orange-50 px-2 py-0.5 text-[11px] font-medium text-orange-700 border border-orange-200">{{ prospect.contact_status }}</span>
    {% else %}
    <span class="inline-flex items-center rounded-sm bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-600 border border-gray-200">{{ prospect.contact_status }}</span>
    {% endif %}
    {% if prospect.email_redacted %}<p class="mt-1.5 text-[11px] font-mono text-notion-text/80 bg-gray-50 px-1.5 py-0.5 rounded-sm inline-block">{{ prospect.email_redacted }}</p>{% endif %}
  </td>
  <td class="px-4 py-4 align-top">
    <span class="inline-flex items-center rounded-sm bg-[#f9f9f8] px-2 py-0.5 text-[11px] font-medium text-notion-text border border-notion-border shadow-sm">{{ prospect.acquisition_stage }}</span>
  </td>
  <td class="px-4 py-4 align-top text-right">
    <div class="flex flex-col items-end gap-1.5 opacity-80 group-hover:opacity-100 transition-opacity">
      <a
        href="{{ linkedin_people_url(prospect.company_name, prospect.decision_maker_name, prospect.decision_maker_title) }}"
        target="_blank" rel="noopener"
        class="inline-flex items-center justify-center px-2 py-1 text-[11px] font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 transition-colors w-24"
      >
        <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/></svg>
        LinkedIn
      </a>
      
      <div class="flex gap-1 justify-end w-full">
        <button type="button" onclick="openEnrich({{ prospect.id }})" class="inline-flex flex-1 items-center justify-center px-2 py-1 text-[11px] font-medium text-gray-700 bg-white border border-gray-300 rounded shadow-sm hover:bg-gray-50 transition-colors">
          Emails
        </button>
        <form hx-post="/prospects/{{ prospect.id }}/deep-enrich" hx-target="#sourcing-row-{{ prospect.id }}" hx-swap="outerHTML" class="flex-1 flex">
          <button type="submit" class="w-full inline-flex items-center justify-center px-2 py-1 text-[11px] font-medium text-gray-700 bg-white border border-gray-300 rounded shadow-sm hover:bg-gray-50 transition-colors" title="Deep enrich">
            Enrich
          </button>
        </form>
      </div>
      
      <div class="flex gap-1 justify-end w-full">
        <a href="/prospects/{{ prospect.id }}" class="inline-flex flex-1 items-center justify-center px-2 py-1 text-[11px] font-medium text-gray-700 bg-gray-100 border border-transparent rounded hover:bg-gray-200 transition-colors">
          Open
        </a>
        {% if prospect.needs_manual_review %}
        <form hx-post="/prospects/{{ prospect.id }}/mark-reviewed" hx-target="#sourcing-row-{{ prospect.id }}" hx-swap="outerHTML" class="flex-1 flex">
          <button type="submit" class="w-full inline-flex items-center justify-center px-2 py-1 text-[11px] font-medium text-white bg-[#0f7b6c] border border-transparent rounded hover:bg-[#0c6356] transition-colors shadow-sm">
            Approve
          </button>
        </form>
        {% endif %}
      </div>
    </div>
  </td>
</tr>
""")
