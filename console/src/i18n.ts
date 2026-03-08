import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
<<<<<<< HEAD
=======
import ru from "./locales/ru.json";
>>>>>>> upstream/main
import zh from "./locales/zh.json";

const resources = {
  en: {
    translation: en,
  },
<<<<<<< HEAD
=======
  ru: {
    translation: ru,
  },
>>>>>>> upstream/main
  zh: {
    translation: zh,
  },
};

i18n.use(initReactI18next).init({
  resources,
  lng: localStorage.getItem("language") || "en",
  fallbackLng: "en",
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
