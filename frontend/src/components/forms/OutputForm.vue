<template>
  <v-form>
    <label>Outputs</label>
    <info-node-search ntype="substance"/>
    <info-node-search ntype="tissue"/>
    <info-node-search ntype="measurement_type"/>
    <info-node-search ntype="method"/>
  </v-form>
</template>

<script>
import InfoNodeSearch from "./InfoNodeSearch";

export default {
  name: "OutputForm",
  components: {
    InfoNodeSearch,
  },
}
</script>