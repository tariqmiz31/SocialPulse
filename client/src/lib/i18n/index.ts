import { createIntl, createIntlCache } from 'react-intl';
import type { IntlShape } from 'react-intl';
import arMessages from './messages/ar.json';
import enMessages from './messages/en.json';

interface Message {
  [key: string]: string;
}

interface Messages {
  ar: Message;
  en: Message;
}

export const messages: Messages = {
  ar: arMessages,
  en: enMessages,
};

export const defaultLocale = 'en';
export const supportedLocales = ['en', 'ar'] as const;

export type SupportedLocale = typeof supportedLocales[number];

const cache = createIntlCache();

export function getIntl(locale: string = defaultLocale): IntlShape {
  const finalLocale = supportedLocales.includes(locale as SupportedLocale) 
    ? locale 
    : defaultLocale;

  return createIntl(
    {
      locale: finalLocale,
      messages: messages[finalLocale as keyof typeof messages],
    },
    cache,
  );
}

export function getDirection(locale: string): 'rtl' | 'ltr' {
  return locale === 'ar' ? 'rtl' : 'ltr';
}
