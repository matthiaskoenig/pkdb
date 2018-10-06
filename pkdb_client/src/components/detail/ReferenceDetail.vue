<template>
    <div id="reference-detail">
        <v-layout justify-center>
            <v-flex xs12 sm6>
                <heading-toolbar :title="reference.name" :icon="icon('reference')" :resource_url="resource_url"/>
                <v-card max-width="1000">
                    <b>{{ reference.title }}</b><br/>
                    <get-data v-for="author_url in reference.authors" :resource_url="author_url">
                        <span slot-scope="author">
                        {{ author.data.first_name }} {{ author.data.last_name }},
                        </span>
                    </get-data>
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