<template>
    <div id="reference-detail">
        <v-card max-width="1000" flat>

            <v-icon>{{ icon('reference') }}</v-icon>&nbsp;<strong>{{ reference.title }}</strong><br />
            <span v-for="(author, index) in reference.authors" :key="index">
                {{ author.first_name }} {{ author.last_name }},
            </span><br />
            <i>{{ reference.journal }}, {{reference.date}}</i><br/>

            <a :href="'https://www.ncbi.nlm.nih.gov/pubmed/'+reference.pmid" title="PubMed" target="_blank">PMID:{{reference.pmid }}</a><br/>

            <file-chip v-if="reference.pdf" :file="reference.pdf"></file-chip>
            <warning-chip v-else title="No PDF or no permission"></warning-chip><br />
            {{reference.abstract}}<br/>

        </v-card>
    </div>
</template>

<script>
    import {lookup_icon} from "@/icons"
    import WarningChip from "./WarningChip";


    export default {
        name: "ReferenceDetail",
        components: {WarningChip},
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