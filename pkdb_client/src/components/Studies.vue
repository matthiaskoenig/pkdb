<template>
    <div class="container-fluid">
        <div class="row">
            <div class="col-1" />
            <div class="col-10" >
                <h1><font-awesome-icon icon="procedures" /> Studies <span v-if="count">({{ count }})</span></h1>
            </div>
            <div class="col-1" >
                <a :href="resource_url" title="JSON" target="_blank"><font-awesome-icon icon="code"/></a>
            </div>
        </div>
        <div class="row">
            <v-paginator :resource_url="resource_url" @update="updateResource"></v-paginator>
            <table v-if="count" class="table table-responsive table-condensed table-hover">
                <thead>
                <tr>
                    <th>pk</th>
                    <th>pkdb_version</th>
                    <th>name</th>
                    <th>reference</th>
                    <th>creator</th>
                    <th>curators</th>
                    <th>substances</th>
                    <th>files</th>
                    <th>groupset</th>
                    <th>individualset</th>
                    <th>interventionset</th>
                    <th>outputset</th>
                    <th>timecourseset</th>
                    <th>design</th>
                    <th>keywords</th>
                </tr>
                </thead>
                <tbody>
                <tr v-for="(entry, index) in entries" :key="index">
                    <td><font-awesome-icon icon="procedures" /> {{ entry.pk }}</td>
                    <td>{{ entry.pkdb_version }}</td>
                    <td>{{ entry.name }}</td>
                    <td><a v-if="entry.reference" :href="entry.reference" :title="entry.reference"><font-awesome-icon icon="file-alt" /></a></td>
                    <td><a v-if="entry.creator" :href="entry.creator" :title="entry.creator"><font-awesome-icon icon="user-cog" /></a></td>
                    <td><span v-for="(c, index2) in entry.curators" :key="index2">
                        <a :href="c" :title="c"><font-awesome-icon icon="user-edit" /></a>&nbsp;</span>
                    </td>
                    <td><span v-for="(c, index2) in entry.substances" :key="index2">
                        <a :href="c" :title="c"><font-awesome-icon icon="tablets" /></a>&nbsp;</span>
                    </td>
                    <td><span v-for="(f, index2) in entry.files" :key="index2">
                        <a :href="f" :title="f"><font-awesome-icon icon="file-medical" /></a>&nbsp;</span>
                    </td>
                    <td><a v-if="entry.groupset" :href="entry.groupset" :title="entry.groupset"><font-awesome-icon icon="users" /></a></td>
                    <td><a v-if="entry.individualset" :href="entry.individualset" :title="entry.individualset"><font-awesome-icon icon="user" /></a></td>
                    <td><a v-if="entry.interventionset" :href="entry.interventionset" :title="entry.interventionset"><font-awesome-icon icon="capsules" /></a></td>
                    <td><a v-if="entry.outputset" :href="entry.outputset" :title="entry.outputset"><font-awesome-icon icon="chart-bar" /></a></td>
                    <td><a v-if="entry.timecourseset" :href="entry.timecourseset" :title="entry.timecourseset"><font-awesome-icon icon="chart-bar" /></a></td>
                    <td>{{ entry.design }}</td>
                    <td><span v-for="(c, index2) in entry.keywords" :key="index2">
                        <a :href="c" :title="c"><font-awesome-icon icon="tablets" /></a>&nbsp;</span>
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
        name: 'Studies',
        components: {
            VPaginator: VuePaginator
        },
        props: {
            api: String
        },
        methods:{
            updateResource(data){
                this.entries = data.data;
                this.count = data.count
            }
        },
        data() {
            return {
                // The resource variable
                entries: [],
                // Here you define the url of your paginated API
                resource_url: this.api + '/studies_read/?format=json',
                count: null,
            }
        }
    }
</script>

<style></style>