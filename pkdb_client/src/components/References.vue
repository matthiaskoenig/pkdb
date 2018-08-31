<template>
    <div>
        <h1>References <span v-if="count">({{ count }})</span></h1>
        <v-paginator :resource_url="resource_url"  @update="updateResource"></v-paginator>
        <table v-if="count" class="table table-responsive table-condensed table-hover">
            <thead>
            <tr>
                <th>sid</th>
                <th>pmid</th>
                <th>name</th>
                <th>title</th>
                <th>journal</th>
                <th>date</th>
                <th>abstract</th>
            </tr>
            </thead>
            <tbody>
            <tr v-for="(reference, index) in references" :key="index">
                <td>{{ reference.sid }}</td>
                <td><a :href="'https://www.ncbi.nlm.nih.gov/pubmed/'+reference.pmid" target="_blank">{{ reference.pmid }}</a></td>
                <td>{{ reference.name }}</td>
                <td>{{ reference.title }}</td>
                <td>{{ reference.journal }}</td>
                <td>{{ reference.date }}</td>
                <td>{{ reference.abstract }}</td>
            </tr>
            </tbody>
        </table>
    </div>
</template>
<script>

import VuePaginator from 'vuejs-paginator';
export default {
    name: 'References',
    components: {
        VPaginator: VuePaginator
    },
    props: {
        api: String
    },
    methods:{
        updateResource(data){
            this.references = data.data
            this.count = data.count
        }
    },
    data() {
        return {
            references: [],
            count: null,
            resource_url: this.api + '/references/?format=json',
            }
        }
}
</script>
<style>

</style>