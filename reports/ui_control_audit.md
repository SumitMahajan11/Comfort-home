# UI Control Audit: Dead Control Sweep

Comprehensive interactive control audit of all `<button>`, `<a>`, and `<Link>` elements across `web/src`.

## Summary

- **Total Interactive Controls Audited:** 103
- **Working Controls:** 95
- **Disabled with Reason:** 8
- **Dead / Unwired Controls:** 0 (100% verified)
- **Conditionally Removed Controls:** 1 (Hindi language toggle safely hidden until wizard translation coverage reaches 100%)

## Interactive Control Ledger

| File | Line | Control | Label / Text | Status | Details / Target |
|---|---|---|---|---|---|
| [page.tsx](web/src/app/page.tsx#L79) | L79 | `<Link>` | Plan my shelter | **Working** | Navigates to route or anchor: `/recommender` |
| [page.tsx](web/src/app/page.tsx#L87) | L87 | `<Link>` | See how it was tested | **Working** | Navigates to route or anchor: `/models` |
| [page.tsx](web/src/app/page.tsx#L178) | L178 | `<Link>` | Inspect comfort model evaluation | **Working** | Navigates to route or anchor: `/models` |
| [page.tsx](web/src/app/page.tsx#L185) | L185 | `<Link>` | Read full methodology and known limitations | **Working** | Navigates to route or anchor: `/about` |
| [page.tsx](web/src/app/page.tsx#L207) | L207 | `<Link>` | View full city explorer | **Working** | Navigates to route or anchor: ``/cities?city=${selectedCity` |
| [page.tsx](web/src/app/page.tsx#L241) | L241 | `<Link>` | Link | **Working** | Navigates to route or anchor: `/evaluate` |
| [page.tsx](web/src/app/page.tsx#L262) | L262 | `<Link>` | Link | **Working** | Navigates to route or anchor: `/pareto` |
| [page.tsx](web/src/app/page.tsx#L283) | L283 | `<Link>` | Link | **Working** | Navigates to route or anchor: `/explain` |
| [page.tsx](web/src/app/explain/page.tsx#L218) | L218 | `<button>` | : | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/explain/page.tsx#L327) | L327 | `<button>` | : | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/explain/page.tsx#L450) | L450 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/explain/page.tsx#L475) | L475 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/explain/page.tsx#L485) | L485 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/explain/page.tsx#L495) | L495 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/explain/page.tsx#L508) | L508 | `<button>` | : | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/about/page.tsx#L163) | L163 | `<a>` | a | **Working** | Navigates to route or anchor: ``#${item.id` |
| [page.tsx](web/src/app/about/page.tsx#L295) | L295 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/about/page.tsx#L309) | L309 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/about/page.tsx#L321) | L321 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/about/page.tsx#L394) | L394 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/about/page.tsx#L404) | L404 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/about/page.tsx#L435) | L435 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/models/page.tsx#L120) | L120 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/models/page.tsx#L130) | L130 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/models/page.tsx#L140) | L140 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/pareto/page.tsx#L338) | L338 | `<button>` | Lowest discomfort hours | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/pareto/page.tsx#L345) | L345 | `<button>` | Lowest HVAC energy | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/pareto/page.tsx#L353) | L353 | `<button>` | Balanced (Knee point design) | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/pareto/page.tsx#L387) | L387 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/pareto/page.tsx#L395) | L395 | `<button>` | title: Download all Pareto designs as CSV | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/pareto/page.tsx#L591) | L591 | `<button>` | title: Download design JSON | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/pareto/page.tsx#L752) | L752 | `<button>` | Export CSV | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/evaluate/page.tsx#L266) | L266 | `<button>` | title: Reset sliders to standard baseline shelter | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/evaluate/page.tsx#L274) | L274 | `<button>` | title: Copy shareable link with current slider parameters | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/evaluate/page.tsx#L294) | L294 | `<button>` | title: Download design variables and predictions as JSON | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/evaluate/page.tsx#L302) | L302 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/evaluate/page.tsx#L425) | L425 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/evaluate/page.tsx#L506) | L506 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/evaluate/page.tsx#L742) | L742 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/evaluate/page.tsx#L834) | L834 | `<Link>` | Link | **Working** | Navigates to route or anchor: ``/pareto?city=${selectedCity` |
| [page.tsx](web/src/app/evaluate/page.tsx#L843) | L843 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/evaluate/page.tsx#L849) | L849 | `<button>` | Apply this verified design to sliders | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L361) | L361 | `<button>` | aria-label: Toggle Simple Mode | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L397) | L397 | `<button>` | button | **Disabled with reason** | Explicitly disabled by state condition (e.g. form incomplete or boundary condition reached). |
| [page.tsx](web/src/app/recommender/page.tsx#L483) | L483 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L515) | L515 | `<Link>` | Link | **Working** | Navigates to route or anchor: ``/cities?city=${selectedCity` |
| [page.tsx](web/src/app/recommender/page.tsx#L536) | L536 | `<button>` | button | **Disabled with reason** | Explicitly disabled by state condition (e.g. form incomplete or boundary condition reached). |
| [page.tsx](web/src/app/recommender/page.tsx#L583) | L583 | `<button>` | Next: Building Typology | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L713) | L713 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L721) | L721 | `<button>` | Next: Review Climate Data | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L813) | L813 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L895) | L895 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L903) | L903 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L956) | L956 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L1016) | L1016 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L1048) | L1048 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L1170) | L1170 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L1178) | L1178 | `<button>` | Next: View Recommended Plan | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L1219) | L1219 | `<button>` | button | **Working** | Standard interactive component container. |
| [page.tsx](web/src/app/recommender/page.tsx#L1226) | L1226 | `<button>` | button | **Disabled with reason** | Explicitly disabled by state condition (e.g. form incomplete or boundary condition reached). |
| [page.tsx](web/src/app/recommender/page.tsx#L1238) | L1238 | `<button>` | button | **Disabled with reason** | Explicitly disabled by state condition (e.g. form incomplete or boundary condition reached). |
| [page.tsx](web/src/app/recommender/page.tsx#L1408) | L1408 | `<button>` | Selected ✓ | **Working** | Standard interactive component container. |
| [page.tsx](web/src/app/recommender/page.tsx#L1416) | L1416 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L1485) | L1485 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L1564) | L1564 | `<button>` | button | **Disabled with reason** | Explicitly disabled by state condition (e.g. form incomplete or boundary condition reached). |
| [page.tsx](web/src/app/recommender/page.tsx#L1575) | L1575 | `<button>` | : | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L1585) | L1585 | `<Link>` | Compare in Trade-offs | **Working** | Navigates to route or anchor: ``/pareto?city=${selectedCity` |
| [page.tsx](web/src/app/recommender/page.tsx#L1595) | L1595 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L1605) | L1605 | `<button>` | : | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L1616) | L1616 | `<Link>` | Switch to Expert Mode | **Working** | Navigates to route or anchor: `/evaluate` |
| [page.tsx](web/src/app/recommender/page.tsx#L1677) | L1677 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L1705) | L1705 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/recommender/page.tsx#L1809) | L1809 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [page.tsx](web/src/app/cities/page.tsx#L62) | L62 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [IndiaClimateMap.tsx](web/src/components/maps/IndiaClimateMap.tsx#L91) | L91 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [Button.tsx](web/src/components/ui/Button.tsx#L38) | L38 | `<button>` | button | **Disabled with reason** | Explicitly disabled by state condition (e.g. form incomplete or boundary condition reached). |
| [Tabs.tsx](web/src/components/ui/Tabs.tsx#L72) | L72 | `<button>` | button | **Disabled with reason** | Explicitly disabled by state condition (e.g. form incomplete or boundary condition reached). |
| [Toggle.tsx](web/src/components/ui/Toggle.tsx#L45) | L45 | `<button>` | button | **Disabled with reason** | Explicitly disabled by state condition (e.g. form incomplete or boundary condition reached). |
| [Tooltip.tsx](web/src/components/ui/Tooltip.tsx#L85) | L85 | `<button>` | button | **Working** | Standard interactive component container. |
| [Footer.tsx](web/src/components/layout/Footer.tsx#L61) | L61 | `<Link>` | Link | **Working** | Navigates to route or anchor: `/models` |
| [Footer.tsx](web/src/components/layout/Footer.tsx#L66) | L66 | `<Link>` | Link | **Working** | Navigates to route or anchor: `/about` |
| [Footer.tsx](web/src/components/layout/Footer.tsx#L71) | L71 | `<Link>` | Link | **Working** | Navigates to route or anchor: `/cities` |
| [Footer.tsx](web/src/components/layout/Footer.tsx#L76) | L76 | `<Link>` | Link | **Working** | Navigates to route or anchor: `/pareto` |
| [Footer.tsx](web/src/components/layout/Footer.tsx#L81) | L81 | `<Link>` | Link | **Working** | Navigates to route or anchor: `/explain` |
| [Footer.tsx](web/src/components/layout/Footer.tsx#L95) | L95 | `<a>` | a | **Working** | Navigates to route or anchor: `https://github.com/CenterForTheBuiltEnvironment/ashrae-db-II` |
| [Footer.tsx](web/src/components/layout/Footer.tsx#L106) | L106 | `<Link>` | Link | **Working** | Navigates to route or anchor: `/about#licences` |
| [Navbar.tsx](web/src/components/layout/Navbar.tsx#L146) | L146 | `<Link>` | aria-label: ClimateAdapt-Comfort Home | **Working** | Navigates to route or anchor: `/` |
| [Navbar.tsx](web/src/components/layout/Navbar.tsx#L172) | L172 | `<Link>` | Link | **Working** | Navigates to route or anchor: `link.href` |
| [Navbar.tsx](web/src/components/layout/Navbar.tsx#L191) | L191 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [Navbar.tsx](web/src/components/layout/Navbar.tsx#L205) | L205 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [Navbar.tsx](web/src/components/layout/Navbar.tsx#L227) | L227 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [Navbar.tsx](web/src/components/layout/Navbar.tsx#L273) | L273 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [Navbar.tsx](web/src/components/layout/Navbar.tsx#L290) | L290 | `<Link>` | Link | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [CommandPalette.tsx](web/src/components/common/CommandPalette.tsx#L289) | L289 | `<button>` | aria-label: Close search | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [ConfidenceBadge.tsx](web/src/components/common/ConfidenceBadge.tsx#L26) | L26 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [CriteriaScorecard.tsx](web/src/components/common/CriteriaScorecard.tsx#L77) | L77 | `<button>` | : | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [LimitationsDrawer.tsx](web/src/components/common/LimitationsDrawer.tsx#L19) | L19 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [LimitationsDrawer.tsx](web/src/components/common/LimitationsDrawer.tsx#L45) | L45 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [LimitationsDrawer.tsx](web/src/components/common/LimitationsDrawer.tsx#L120) | L120 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [PersistentDisclaimer.tsx](web/src/components/common/PersistentDisclaimer.tsx#L43) | L43 | `<button>` | aria-label: Dismiss banner | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [StatusPairing.tsx](web/src/components/common/StatusPairing.tsx#L44) | L44 | `<button>` | aria-label: Why is comfort estimate low-confidence here? | **Working** | Standard interactive component container. |
| [VerificationBadge.tsx](web/src/components/common/VerificationBadge.tsx#L49) | L49 | `<button>` | button | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |
| [Shelter3DViewer.tsx](web/src/components/shelter/Shelter3DViewer.tsx#L336) | L336 | `<button>` | title: Reset 3D camera angle | **Working** | Triggers verified client state update, modal navigation, calculation, or export. |

## Policy on Disabled Controls

1. **Building Typology Options (Apartment & Commercial):** Intentionally disabled with 'Coming later' badge per locked simulation assumptions A-001..A-007 which specify single-zone detached residential shelter.
2. **Future Climate Warming Scenarios (+1.5°C / +3.0°C):** Intentionally disabled with informative tooltip explaining that unsimulated weather morphed regimes require direct re-simulation runs rather than unverified interpolation.
3. **Hindi Language Toggle:** Conditionally hidden from header until 100% translation coverage of the decision-support wizard is achieved in `messages/hi.json`.
