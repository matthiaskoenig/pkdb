<template>
  <v-form>
    <label>Subjects</label>
    <measurement-type-choice-search ntype="measurement_type"/>
  </v-form>
</template>


<script>
import MeasurementTypeChoiceSearch from "./MeasurementTypeChoiceSearch";

export default {
  name: "SubjectForm",
  components: {
    MeasurementTypeChoiceSearch
  },
  data() {
    return {
      NumberMeasurementChoices: 1
    }
  }
}
</script>