<template>
    <div id="about">

        <h1>Characteristica Options</h1>
        <get-data :resource_url="characteristica_options_url">
          <template slot-scope="characteristica">
              <options-browser :options="characteristica.data" />
          </template>
        </get-data>

        <h1>Intervention Options</h1>
        <get-data :resource_url="intervention_options_url">
            <template slot-scope="intervention">
                <options-browser :options="intervention.data" />
            </template>
        </get-data>
    </div>
</template>

<script>
    import OptionsBrowser from "./detail/OptionsBrowser"

    export default {
        name: "Curation",
        components: {
            OptionsBrowser
        },
        computed: {
            characteristica_options_url() {
                return this.$store.state.endpoints.api + '/characteristica_options/';
            },
            intervention_options_url() {
                return this.$store.state.endpoints.api + '/intervention_options/';
            },
        }
    }
</script>

<style scoped>

</style>