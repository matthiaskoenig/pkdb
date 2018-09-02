<template>
    <div class="container-fluid">
        <div class="row">
            <div class="col-1" />
            <div class="col-10" >
                <h1><font-awesome-icon icon="capsules" /> Interventions <span v-if="count">({{ count }})</span></h1>
            </div>
            <div class="col-1" >
                <a :href="resource_url" title="JSON" target="_blank"><font-awesome-icon icon="code"/></a>
            </div>
        </div>
        <div class="row">
            <v-paginator :resource_url="resource_url"  @update="updateResource"></v-paginator>
            <table v-if="count" class="table table-responsive table-condensed table-hover">
                <thead>
                <tr>
                    <th>pk</th>
                    <th>name</th>
                    <th>category</th>
                    <th>choice</th>
                    <th>route</th>
                    <th>form</th>
                    <th>application</th>
                    <th>substance</th>
                    <th>time</th>
                    <th>time unit</th>
                    <th>unit</th>
                    <th>value</th>
                    <th>mean</th>
                    <th>median</th>
                    <th>min</th>
                    <th>max</th>
                    <th>sd</th>
                    <th>se</th>
                    <th>cv</th>
                </tr>
                </thead>
                <tbody>
                <tr v-for="(entry, index) in entries" :key="index">
                    <td><font-awesome-icon icon="capsules" /> {{ entry.pk }}</td>
                    <td>{{ entry.name }}</td>
                    <td>{{ entry.category }}</td>
                    <td>{{ entry.choice }}</td>
                    <td>{{ entry.route }}</td>
                    <td>{{ entry.application }}</td>
                    <td>{{ entry.tissue }}</td>
                    <td><a v-if="entry.substance" :href="entry.substance" :title="entry.substance"><font-awesome-icon icon="tablets" /></a></td>
                    <td>{{ entry.time }}</td>
                    <td>{{ entry.time_unit }}</td>
                    <td>{{ entry.unit }}</td>
                    <td>{{ entry.value }}</td>
                    <td>{{ entry.mean }}</td>
                    <td>{{ entry.median }}</td>
                    <td>{{ entry.min }}</td>
                    <td>{{ entry.max }}</td>
                    <td>{{ entry.sd }}</td>
                    <td>{{ entry.se }}</td>
                    <td>{{ entry.cv }}</td>
                </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>
<script>

import VuePaginator from 'vuejs-paginator';
export default {
    name: 'Interventions',
    components: {
        VPaginator: VuePaginator
    },
    props: {
        api: String
    },
    methods:{
        updateResource(data){
            this.entries = data.data
            this.count = data.count
        }
    },
    data() {
        return {
            entries: [],
            count: null,
            resource_url: this.api + '/interventions_read/?format=json',
            }
        }
}
</script>
<style>

</style>