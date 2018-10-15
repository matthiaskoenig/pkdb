<template>
    <span :class="pulse" id="user-avatar">
        <v-avatar color="red" size="35" :title="username">
            <img v-if="src" :src="src"/>
            <span v-if="!src" class="white--text headline" >{{ initials }}</span>
        </v-avatar>
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
            pulse : "not_pulse"

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
                if (this.search.length > 0 && this.username.includes(this.search)) {
                    this.pulse = "pulse"
                }
                else {
                    this.pulse = "not_pulse"
                }
            }
        }
    }
</script>

<style scoped>
    .not_pulse{
        display: block;
        width: 35px;
        height: 35px;
    }

    .pulse {
        display: block;
        width: 35px;
        height: 35px;
        border-radius: 50%;
        box-shadow: 0 0 0 rgba(204,169,44, 0.4);
        animation: pulse 0.5s infinite;
    }

    @-webkit-keyframes pulse {
        0% {
            -webkit-box-shadow: 0 0 0 0 rgba(204,169,44, 0.4);
        }
        70% {
            -webkit-box-shadow: 0 0 0 10px rgba(204,169,44, 0);
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
            -moz-box-shadow: 0 0 0 10px rgba(204,169,44, 0);
            box-shadow: 0 0 0 10px rgba(204,169,44, 0);
        }
        100% {
            -moz-box-shadow: 0 0 0 0 rgba(204,169,44, 0);
            box-shadow: 0 0 0 0 rgba(204,169,44, 0);
        }
    }

</style>