<template>
  <span>
    <info-node-search query_type="queries" ntype="substance" query_key="interventions__substance_sid__in" />
    <info-node-search query_type="queries" ntype="route"  query_key="interventions__route_sid__in"/>
    <info-node-search query_type="queries" ntype="application"  query_key="interventions__application_sid__in" />
    <info-node-search query_type="queries" ntype="form" query_key="interventions__form_sid__in" />
    <info-node-search query_type="queries" ntype="measurement_type"  query_key="interventions__measurement_type_sid__in"/>
  </span>
</template>


<script>
import StudySearch from "./StudySearch";
import InfoNodeSearch from "./InfoNodeSearch";

export default {
  name: "InterventionSearchForm",
  components: {
    InfoNodeSearch,
    StudySearch,
  }
}
</script>