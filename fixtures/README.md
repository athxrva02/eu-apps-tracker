# Synthetic fixtures

Every candidate and vacancy in this directory is synthetic. `profile.json` is not the supplied private résumé. `vacancies.json` contains 24 labeled examples; `new-vacancy.json` appears on the second demo scan. `role-aliases.json` and `target-companies.json` preserve search intent from the informal requirements; company links are entry-page references, not working integrations.

`connectors/` contains fixed synthetic responses shaped like the documented Greenhouse and Lever APIs, a JSON-LD HTML page, and an `.eml` alert. They are deterministic adapter fixtures, not captures of real vacancies. The email includes a LinkedIn job link to verify import without fetching it.

The synthetic ranking quality gate is at least eight relevant vacancies in the top ten. Current results and limitations are in `docs/validation.md`. The fixture descriptions intentionally exercise concept overlap; this is not a benchmark of real hiring suitability or multilingual comprehension.
