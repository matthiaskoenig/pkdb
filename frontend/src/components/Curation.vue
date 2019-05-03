<template>
    <div id="about">
        <v-layout wrap>
            <v-flex xs3>
                <get-data :resource_url="characteristica_options_url">
                  <template slot-scope="characteristica">
                      <characteristica-browser :options="characteristica.data" title="Characteristica"/>
                  </template>
                </get-data>
            </v-flex>
            <v-flex xs3>
                <get-data :resource_url="intervention_options_url">
                    <template slot-scope="intervention">
                        <characteristica-browser :options="intervention.data" title="Interventions"/>
                    </template>
                </get-data>
            </v-flex>
            <v-flex xs3>
                <get-data :resource_url="output_options_url">
                    <template slot-scope="output">
                        <output-browser :options="output.data" title="PK types"/>
                    </template>
                </get-data>
            </v-flex>
            <v-flex xs3>
                <get-data :resource_url="substances_url">
                    <template slot-scope="substances">
                        <substance-browser :substances="substances.data.data" title="Substances"/>
                    </template>
                </get-data>
            </v-flex>
            <v-flex xs3>
                <get-data :resource_url="keywords_url">
                    <template slot-scope="keywords">
                        <keyword-browser :keywords="keywords.data.data" title="Keywords"/>
                    </template>
                </get-data>
            </v-flex>
        </v-layout>
    </div>
</template>

<script>
    import CharacteristicaBrowser from "./curation/CharacteristicaBrowser"
    import OutputBrowser from "./curation/OutputBrowser"
    import SubstanceBrowser from "./curation/SubstanceBrowser"
    import KeywordBrowser from "./curation/KeywordBrowser"

    export default {
        name: "Curation",
        components: {
            CharacteristicaBrowser,
            OutputBrowser,
            SubstanceBrowser,
            KeywordBrowser
        },
        computed: {
            characteristica_options_url() {
                return this.$store.state.endpoints.api + '/characteristica_options/';
            },
            intervention_options_url() {
                return this.$store.state.endpoints.api + '/intervention_options/';
            },
            output_options_url() {
                return this.$store.state.endpoints.api + '/output_options/';
            },
            substances_url() {
                return this.$store.state.endpoints.api + '/substances_elastic/?page_size=1000';
            },
            keywords_url() {
                return this.$store.state.endpoints.api + '/keywords_elastic/?page_size=1000';
            },

        }
    }
</script>

<style scoped>

</style>