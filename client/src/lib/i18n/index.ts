import { createIntl, createIntlCache } from 'react-intl';
import arMessages from './messages/ar.json';
import enMessages from './messages/en.json';

export const messages = {
  ar: arMessages,
  en: enMessages,
};

export const defaultLocale = 'en';
export const supportedLocales = ['en', 'ar'];

const cache = createIntlCache();

export function getIntl(locale: string = defaultLocale) {
  return createIntl(
    {
      locale: supportedLocales.includes(locale) ? locale : defaultLocale,
      messages: messages[locale as keyof typeof messages],
    },
    cache,
  );
}

export function getDirection(locale: string) {
  return locale === 'ar' ? 'rtl' : 'ltr';
}
