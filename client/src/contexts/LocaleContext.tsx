import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { IntlProvider } from 'react-intl';
import { messages, defaultLocale, type SupportedLocale, getDirection } from '@/lib/i18n';

type LocaleContextType = {
  locale: SupportedLocale;
  setLocale: (locale: SupportedLocale) => void;
  direction: 'rtl' | 'ltr';
};

const LocaleContext = createContext<LocaleContextType>({
  locale: defaultLocale as SupportedLocale,
  setLocale: () => {},
  direction: 'ltr',
});

export function useLocale() {
  const context = useContext(LocaleContext);
  if (!context) {
    throw new Error('useLocale must be used within a LocaleProvider');
  }
  return context;
}

interface LocaleProviderProps {
  children: ReactNode;
}

export function LocaleProvider({ children }: LocaleProviderProps) {
  const [locale, setLocale] = useState<SupportedLocale>(defaultLocale as SupportedLocale);
  const direction = getDirection(locale);

  useEffect(() => {
    document.documentElement.dir = direction;
    document.documentElement.lang = locale;
  }, [direction, locale]);

  const value = {
    locale,
    setLocale,
    direction,
  };

  return (
    <LocaleContext.Provider value={value}>
      <IntlProvider
        messages={messages[locale]}
        locale={locale}
        defaultLocale={defaultLocale}
      >
        {children}
      </IntlProvider>
    </LocaleContext.Provider>
  );
}