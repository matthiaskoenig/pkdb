import { ref, watch } from "vue";
import {
  accountApi,
  profilePayload,
  type ProfileForm,
} from "../../api/account";
import type { EmailAddress } from "../../api/session";
import { useSessionStore } from "../../stores/session";
const blank = (): ProfileForm => ({
  display_name: "",
  affiliation: "",
  title: "",
  github: "",
  orcid: "",
  github_visible: true,
  orcid_visible: true,
});
export function useProfile() {
  const session = useSessionStore();
  const form = ref<ProfileForm>(blank()),
    photo = ref<File | File[] | null>(null),
    newEmail = ref(""),
    curatorReason = ref("");
  watch(
    () => session.profile,
    (value) => {
      form.value = value
        ? {
            display_name: value.display_name,
            affiliation: value.affiliation,
            title: value.title,
            github: value.github,
            orcid: value.orcid,
            github_visible: value.github_visible,
            orcid_visible: value.orcid_visible,
          }
        : blank();
      photo.value = null;
      newEmail.value = "";
      curatorReason.value = "";
    },
    { immediate: true },
  );
  async function saveProfile() {
    if (!session.profile) return;
    await accountApi.saveProfile(profilePayload(form.value, session.profile));
    await session.refreshProfile();
  }
  async function uploadPhoto() {
    const file = Array.isArray(photo.value) ? photo.value[0] : photo.value;
    if (!file) return;
    if (file.size > 5 * 1024 * 1024)
      throw new RangeError("Please choose an image smaller than 5 MiB.");
    await accountApi.avatar(file);
    await session.refreshProfile();
    photo.value = null;
  }
  async function removePhoto() {
    await accountApi.removeAvatar();
    await session.refreshProfile();
  }
  async function addEmail() {
    await accountApi.addEmail(newEmail.value);
    newEmail.value = "";
    await session.refreshProfile();
  }
  async function makePrimary(value: EmailAddress) {
    await accountApi.makePrimary(value.id);
    await session.refreshProfile();
  }
  async function removeEmail(value: EmailAddress) {
    await accountApi.removeEmail(value.id);
    await session.refreshProfile();
  }
  async function resend(value: EmailAddress) {
    await accountApi.resend(value.email);
  }
  async function requestCurator() {
    await accountApi.requestCurator(curatorReason.value.trim());
    curatorReason.value = "";
  }
  return {
    form,
    photo,
    newEmail,
    curatorReason,
    saveProfile,
    uploadPhoto,
    removePhoto,
    addEmail,
    makePrimary,
    removeEmail,
    resend,
    requestCurator,
  };
}
