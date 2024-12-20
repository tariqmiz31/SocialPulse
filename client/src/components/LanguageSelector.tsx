import { Button } from "@/components/ui/button";
import { useLocale } from "@/contexts/LocaleContext";
import { supportedLocales } from "@/lib/i18n";

export function LanguageSelector() {
  const { locale, setLocale } = useLocale();

  return (
    <div className="flex gap-2">
      {supportedLocales.map((lang) => (
        <Button
          key={lang}
          variant={locale === lang ? "secondary" : "ghost"}
          onClick={() => setLocale(lang)}
          className="w-12"
        >
          {lang.toUpperCase()}
        </Button>
      ))}
    </div>
  );
}
