<template>
    <div id="reference-detail">

        <v-layout justify-center>
            <v-flex xs12 sm6>

                <v-toolbar color="gray" dense max-with="1000">
                    <v-toolbar-title>
                        <Heading :title="reference.name" :icon="icon('reference')"
                                 :resource_url="resource_url"/>
                    </v-toolbar-title>
                </v-toolbar>

                <v-card max-width="1000">
                    <b>{{ reference.title }}</b><br/>
                    <GetData v-for="author_url in reference.authors" :resource_url="author_url">
                        <span slot-scope="author">
                        {{ author.data.first_name }} {{ author.data.last_name }},
                        </span>
                    </GetData>
                    <br />
                    <i>{{ reference.journal }}, {{reference.date}}</i><br/>
                    <a :href="'https://www.ncbi.nlm.nih.gov/pubmed/'+reference.pmid" target="_blank">PMID:{{reference.pmid }}</a><br/>
                    <br />
                    {{reference.abstract}}<br/>
                </v-card>

            </v-flex>
        </v-layout>
    </div>
</template>

<script>
    import {lookup_icon} from "@/icons"

    export default {
        name: "ReferenceDetail",
        props: {
            reference: {
                type: Object,
            },
            resource_url: {
                type: String
            }
        },
        computed: {
        },
        methods: {
            icon: function (key) {
                return lookup_icon(key)
            },
        }
    }
</script>

<style scoped>
.v-card{
    padding: 10px;
}
</style>