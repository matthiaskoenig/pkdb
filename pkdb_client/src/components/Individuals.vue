<template>
    <div class="container-fluid">
        <div class="row">
            <div class="col-1" />
            <div class="col-10" >
                <h1><font-awesome-icon icon="user" /> Indivduals <span v-if="count">({{ count }})</span></h1>
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
                    <th>group</th>
                    <th>characteristica</th>
                </tr>
                </thead>
                <tbody>
                <tr v-for="(entry, index) in entries" :key="index">
                    <td><font-awesome-icon icon="user" /> {{ entry.pk }}</td>
                    <td>{{ entry.name }}</td>
                    <td><a v-if="entry.group" :href="entry.group" :title="entry.group"><font-awesome-icon icon="users" /></a></td>
                    <td><span v-for="(c, index2) in entry.characteristica" :key="index2">
                        <a :href="c" :title="c"><font-awesome-icon icon="cube" /></a>&nbsp;</span>
                    </td>
                </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>
<script>

import VuePaginator from 'vuejs-paginator';
export default {
    name: 'Individuals',
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
            resource_url: this.api + '/individuals_read/?format=json',
            }
        }
}
</script>
<style>

</style>