import { createContext, useContext, useState, useEffect } from 'react';
import { IntlProvider } from 'react-intl';
import { messages, defaultLocale, supportedLocales, getDirection } from '@/lib/i18n';

type LocaleContextType = {
  locale: string;
  setLocale: (locale: string) => void;
  direction: 'rtl' | 'ltr';
};

const LocaleContext = createContext<LocaleContextType>({
  locale: defaultLocale,
  setLocale: () => {},
  direction: 'ltr',
});

export function useLocale() {
  return useContext(LocaleContext);
}

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState(defaultLocale);
  const direction = getDirection(locale);

  useEffect(() => {
    document.documentElement.dir = direction;
    document.documentElement.lang = locale;
  }, [direction, locale]);

  return (
    <LocaleContext.Provider value={{ locale, setLocale, direction }}>
      <IntlProvider
        messages={messages[locale as keyof typeof messages]}
        locale={locale}
        defaultLocale={defaultLocale}
      >
        {children}
      </IntlProvider>
    </LocaleContext.Provider>
  );
}
