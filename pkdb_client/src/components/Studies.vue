<template>
    <div class="container">
        <div class="row">
            <div class="col-1" />
            <div class="col-10" >
                <h1><font-awesome-icon icon="file-alt" /> Studies <span v-if="count">({{ count }})</span></h1>
            </div>
            <div class="col-1" >
                <a :href="api+'/statistics/?format=json'" title="JSON" target="_blank"><font-awesome-icon icon="code"/></a>
            </div>
        </div>
        <div class="row">
            <v-paginator :resource_url="resource_url" @update="updateResource"></v-paginator>
            <table v-if="count" class="table table-responsive table-condensed table-hover">
                <thead>
                <tr>
                    <th>sid</th>
                    <th>pkdb_version</th>
                    <th>name</th>
                    <th>reference</th>
                    <th>creator</th>
                    <th>curators</th>
                    <th>substances</th>
                    <th>design</th>
                    <th>files</th>
                </tr>
                </thead>
                <tbody>
                <tr v-for="(study, index) in studies" :key="index">
                    <td>{{ study.sid }}</td>
                    <td>{{ study.pkdb_version }}</td>
                    <td>{{ study.name }}</td>
                    <td>{{ study.reference }}</td>
                    <td>{{ study.creator }}</td>
                    <td>
                        <li v-for="(curator, index) in study.curators" :key="index">
                            {{ curator }}
                        </li>
                    </td>
                    <td>
                        <li v-for="(substance, index) in study.substances" :key="index">
                            {{ substance }}
                        </li>
                    </td>
                    <td>{{ study.design }}</td>
                    <td>
                        <li v-for="(file, index) in study.files" :key="index">
                            <a :href="file">{{ file }}</a>
                        </li>
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
                this.studies = data.data
                this.count = data.count
            }
        },
        data() {
            return {
                // The resource variable
                studies: [],
                // Here you define the url of your paginated API
                resource_url: this.api + '/studies/?format=json',
                count: null,
            }
        }
    }
</script>

<style></style>