<template>
    <span id="user-avatar">
         <v-chip :class="pulse">
          <v-avatar>
            <img :src="src">
          </v-avatar>
             <text-highlight :queries="search.split(/[ ,]+/)">{{ username }} </text-highlight>
        </v-chip>


        <!--
        <v-avatar  color="red" size="35" :title="username">
            <img :class="pulse" v-if="src" :src="src"/>
            <span :class="pulse" v-if="!src" class="white--text headline" >{{ initials }}</span>
        </v-avatar>
        -->
    </span>
</template>

<script>
    export default {
        name: "UserAvatar",
        props: {
            search: String,
            user: {
                type: Object,
                required: true,
            }
        },
        watch: {
            search: {
                handler() {
                    this.calculate_size()
                },
            }
        },
        data() {return {
            pulse : ""

        }},
        computed: {
            username() {
                return this.user.first_name + ' ' + this.user.last_name;
            },
            initials() {
                return this.user.first_name[0] + this.user.last_name[0];
            },
            src() {
                var img_dir = '/assets/images/avatars/';
                if (this.initials === 'MK'){
                    return img_dir + 'koenig_128.png';
                } else if (this.initials === 'JG'){
                    return img_dir + 'grzegorzewski_128.png';
                }
                return null;
            },

        },
        methods:{
            calculate_size(){
                if (this.search.length > 0 && this.username.toLowerCase().includes(this.search.toLowerCase())) {
                    this.pulse = "pulse"
                }
                else {
                    this.pulse = ""
                }
            }
        }
    }
</script>

<style scoped>
    .pulse {
        animation: pulse 0.5s infinite;
    }
    @-webkit-keyframes pulse {
        0% {
            -webkit-box-shadow: 0 0 0 0 rgba(204,169,44, 0.4);
        }
        70% {
            -webkit-box-shadow: 0 0 0 15px rgba(204,169,44, 0);
        }
        100% {
            -webkit-box-shadow: 0 0 0 0 rgba(204,169,44, 0);
        }
    }
    @keyframes pulse {
        0% {
            -moz-box-shadow: 0 0 0 0 rgba(204,169,44, 0.4);
            box-shadow: 0 0 0 0 rgba(204,169,44, 0.4);
        }
        70% {
            -moz-box-shadow: 0 0 0 15px rgba(204,169,44, 0);
            box-shadow: 0 0 0 15px rgba(204,169,44, 0);
        }
        100% {
            -moz-box-shadow: 0 0 0 0 rgba(204,169,44, 0);
            box-shadow: 0 0 0 0 rgba(204,169,44, 0);
        }
    }

</style>