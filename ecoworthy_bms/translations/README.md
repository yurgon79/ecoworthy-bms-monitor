# Translations

The app is translatable via Qt Linguist. English is the source language and
ships built-in; other languages are community-contributed `.qm` files dropped
in this folder as `app_<locale>.qm` (e.g. `app_de.qm`, `app_fr.qm`,
`app_es_MX.qm`). They load automatically for the matching system locale.

## Contributing a language

1. Generate/update the catalog from source (PySide6 tools):

   ```
   pyside6-lupdate $(git ls-files 'ecoworthy_bms/**/*.py') -ts ecoworthy_bms/translations/app_<locale>.ts
   ```

2. Translate strings in **Qt Linguist**:

   ```
   pyside6-linguist ecoworthy_bms/translations/app_<locale>.ts
   ```

3. Compile to a binary catalog:

   ```
   pyside6-lrelease ecoworthy_bms/translations/app_<locale>.ts -qm ecoworthy_bms/translations/app_<locale>.qm
   ```

4. Run the app under that locale to check it, then open a PR with the `.ts`
   (source) and `.qm` (compiled).

Strings are marked with `self.tr("…")` in the widgets. If you find an
unmarked user-facing string, wrap it and include that in your PR.
