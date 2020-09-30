<template>
  <v-btn color="black"
         text
         width="100%"
         to="/data"
         title="Browse PK-DB data"
  >
    <v-icon left color="#1E90FF">{{ faIcon('data') }}</v-icon>
    data
  </v-btn>
</template>

<script>
import {IconsMixin} from "../../../icons";

export default {
  name: "DataButton",
  mixins: [IconsMixin]

}
</script>

<style scoped>

</style>