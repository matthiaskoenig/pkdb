<template>
  <div>

  <object-chip  v-if="Object.keys(measurement_type).length !== 0"
                v-for="measurement_type in details.measurement_type"
                :object="measurement_type"
                :key="measurement_type.sid"
                otype="measurement_type"
  />
  <object-chip v-if="Object.keys(tissue).length !== 0"
               v-for="tissue in details.tissue"
               :object="tissue"
               :key="tissue.sid"
               otype="tissue"
  />
  <object-chip v-if="Object.keys(substance).length !== 0"
               v-for="substance in details.substance"
               :object="substance"
               :key="substance.sid"
               otype="substance"
              />
    <span v-if="details.interventions.length > 0" v-for="(interventions , index2) in details.interventions" :key="index2">
      <object-chip
          v-for="intervention in interventions"
          :object="intervention"
          otype="intervention"
          :key="intervention.pk"
      />
    </span>
    <br />
    <!--

    <object-chip


        otype="group"
        v-if="Object.keys(group).length !== 0"
        v-for="group in details.group"
        :object="group"
        :key="group.pk"
  />
    <object-chip
        otype="individual"
        v-if="Object.keys(individual).length !== 0"
        v-for="individual in details.individual"
        :object="individual"
        :key="individual.pk"
    />
    -->

  </div>

</template>

<script>

export default {
  name: "ScatterDetails",
  props: {
    details: {
      type: Object,
      required: true,
    }
  }
}
</script>

<style scoped>

</style>