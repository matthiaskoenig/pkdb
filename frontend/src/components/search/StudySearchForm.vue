<template>
 <div>
      <study-search/>
      <user-search on="creator"/>
      <user-search on="curators" />
 </div>
</template>

<script>
import StudySearch from "./StudySearch";
import UserSearch from "./UserSearch";

export default {
  name: "StudySearchForm",
  components: {
    StudySearch,
    UserSearch,
  }
}
</script>